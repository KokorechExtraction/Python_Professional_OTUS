import collections
import gzip
import glob
import logging
import os
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
import sys
import threading
import time
from optparse import OptionParser

import queue

import appsinstalled_pb2

import memcache




NORMAL_ERR_RATE = 0.01


AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


def dot_rename(path):
    head, fn = os.path.split(path)
    os.rename(path, os.path.join(head, "." + fn))


def iter_files_chronological(pattern):
    files = glob.glob(pattern)
    files.sort()
    return files


def parse_appsinstalled(line):
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return None
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def make_key_and_value(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    ua.apps.extend(appsinstalled.apps)

    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    packed = ua.SerializeToString()
    return key, packed, ua


class WorkerStats:
    def __init__(self):
        self.processed = 0
        self.errors = 0



class MemcacheWorker(threading.Thread):
    def __init__(self, memc_addr, q, dry_run, batch_size, socket_timeout, retry, retry_backoff, stats, stats_lock):
        super().__init__()
        self.daemon = True
        self.memc_addr = memc_addr
        self.q = q
        self.dry_run = dry_run
        self.batch_size = max(1, int(batch_size))
        self.socket_timeout = float(socket_timeout)
        self.retry = max(0, int(retry))
        self.retry_backoff = float(retry_backoff)

        self.stats = stats
        self.stats_lock = stats_lock

        self._client = None

    def _get_client(self):

        if self._client is None:
            self._client = memcache.Client([self.memc_addr], socket_timeout=self.socket_timeout)
        return self._client

    def _flush(self, batch):

        if not batch:
            return

        if self.dry_run:
            with self.stats_lock:
                self.stats.ok += len(batch)
            return

        payload = dict(batch)
        client = self._get_client()

        attempt = 0
        while True:
            try:
                failed_keys = client.set_multi(payload)
                if failed_keys:
                    with self.stats_lock:
                        self.stats.err += len(failed_keys)
                        self.stats.ok += (len(payload) - len(failed_keys))
                    logging.error("%s - failed keys: %s", self.memc_addr, len(failed_keys))
                else:
                    with self.stats_lock:
                        self.stats.ok += len(payload)
                return
            except Exception as e:
                attempt += 1
                logging.exception("Cannot write to memc %s (attempt %s): %s", self.memc_addr, attempt, e)
                if attempt > self.retry:
                    with self.stats_lock:
                        self.stats.err += len(payload)
                    return
                time.sleep(self.retry_backoff * attempt)

    def run(self):

        batch = []
        while True:
            item = self.q.get()
            try:
                if item is None:

                    self._flush(batch)
                    return
                batch.append(item)
                if len(batch) >= self.batch_size:
                    self._flush(batch)
                    batch = []
            finally:
                self.q.task_done()


def process_file(
    fn,
    device_memc,
    dry_run,
    workers,
    batch_size,
    queue_size,
    socket_timeout,
    retry,
    retry_backoff,
):

    addrs = sorted(set(device_memc.values()))
    if not addrs:
        logging.error("No memcache addresses provided")
        return 0, 0


    qsize = int(queue_size) if queue_size is not None else 0
    q_by_addr = {addr: queue.Queue(maxsize=qsize) for addr in addrs}


    workers_per_addr = max(1, int(workers or 1))


    stats_lock = threading.Lock()
    stats_by_addr = {addr: WorkerStats() for addr in addrs}


    threads = []
    for addr in addrs:
        for _ in range(workers_per_addr):
            t = MemcacheWorker(
                memc_addr=addr,
                q=q_by_addr[addr],
                dry_run=dry_run,
                batch_size=batch_size,
                socket_timeout=socket_timeout,
                retry=retry,
                retry_backoff=retry_backoff,
                stats=stats_by_addr[addr],
                stats_lock=stats_lock,
            )
            t.start()
            threads.append(t)

    errors_parse = 0
    errors_unknown = 0

    logging.info("Processing %s", fn)


    with gzip.open(fn, "rt", encoding="utf-8", errors="replace") as fd:
        for line in fd:
            line = line.rstrip("\r\n")
            if not line:
                continue

            appsinstalled = parse_appsinstalled(line)
            if not appsinstalled:
                errors_parse += 1
                continue

            memc_addr = device_memc.get(appsinstalled.dev_type)
            if not memc_addr:
                errors_unknown += 1
                logging.error("Unknown device type: %s", appsinstalled.dev_type)
                continue

            key, packed, ua = make_key_and_value(appsinstalled)

            if dry_run:
                logging.debug("%s - %s -> %s", memc_addr, key, str(ua).replace("\n", " "))

            q_by_addr[memc_addr].put((key, packed))


    for addr in addrs:
        for _ in range(workers_per_addr):
            q_by_addr[addr].put(None)


    for addr in addrs:
        q_by_addr[addr].join()
    for t in threads:
        t.join()


    processed_ok = sum(stats_by_addr[addr].processed for addr in addrs)
    errors_write = sum(stats_by_addr[addr].errors for addr in addrs)

    errors_total = errors_parse + errors_unknown + errors_write
    return processed_ok, errors_total



def main(options):

    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    files = iter_files_chronological(options.pattern)
    if not files:
        logging.warning("No files matched pattern: %s", options.pattern)
        return 0

    for fn in files:
        processed, errors = process_file(
            fn=fn,
            device_memc=device_memc,
            dry_run=options.dry,
            workers=options.workers,
            batch_size=options.batch,
            queue_size=options.queue_size,
            socket_timeout=options.timeout,
            retry=options.retry,
            retry_backoff=options.retry_backoff,
        )


        if not processed:
            dot_rename(fn)
            logging.warning("No records processed, file renamed anyway: %s", fn)
            continue

        err_rate = float(errors) / float(processed)
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successful load", err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load", err_rate, NORMAL_ERR_RATE)


        dot_rename(fn)

    return 0


def prototest():

    sample = (
        "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\n"
        "gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    )
    for line in sample.splitlines():
        ai = parse_appsinstalled(line)
        assert ai is not None
        _, packed, ua = make_key_and_value(ai)
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()


    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)


    op.add_option("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")


    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")


    op.add_option("--workers", action="store", type="int", default=0,
                  help="Сколько потоков-писателей. 0 => авто (по числу memcache адресов)")
    op.add_option("--batch", action="store", type="int", default=256,
                  help="Размер пачки для set_multi()")
    op.add_option("--queue-size", action="store", type="int", default=50000,
                  help="Макс. размер очереди задач на 1 адрес memcache")
    op.add_option("--timeout", action="store", type="float", default=1.0,
                  help="socket_timeout для python-memcached (сек)")
    op.add_option("--retry", action="store", type="int", default=1,
                  help="Сколько раз повторять отправку пачки при исключении")
    op.add_option("--retry-backoff", action="store", type="float", default=0.05,
                  help="Базовая задержка между ретраями (сек), умножается на номер попытки")

    (opts, _args) = op.parse_args()


    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO if not opts.dry else logging.DEBUG,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )

    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s", opts)
    try:
        sys.exit(main(opts))
    except Exception as e:
        logging.exception("Unexpected error: %s", e)
        sys.exit(1)
