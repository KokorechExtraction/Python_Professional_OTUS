import gzip
import os
from pathlib import Path

import pytest

import memc_load_hw as ml


class FakeMemcacheClient:
    def __init__(self, servers, socket_timeout=1.0):
        self.servers = tuple(servers)
        self.socket_timeout = socket_timeout
        self.storage = {}

    def set_multi(self, mapping):

        for k, v in mapping.items():
            self.storage[k] = v
        return []


@pytest.fixture
def fake_memcache(monkeypatch):
    clients = {}

    def factory(servers, socket_timeout=1.0):

        key = tuple(servers)
        c = clients.get(key)
        if c is None:
            c = FakeMemcacheClient(servers, socket_timeout=socket_timeout)
            clients[key] = c
        return c

    monkeypatch.setattr(ml.memcache, "Client", factory)
    return clients


def make_gz(tmp_path: Path, name: str, lines: str) -> Path:
    p = tmp_path / name
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(lines)
    return p


def test_parse_appsinstalled_ok():
    line = "idfa\tabc\t55.55\t42.42\t1,2,3"
    ai = ml.parse_appsinstalled(line)
    assert ai is not None
    assert ai.dev_type == "idfa"
    assert ai.dev_id == "abc"
    assert ai.lat == 55.55
    assert ai.lon == 42.42
    assert ai.apps == [1, 2, 3]


def test_parse_appsinstalled_bad_coords():
    assert ml.parse_appsinstalled("idfa\tabc\tX\tY\t1,2") is None


def test_process_file_writes_to_right_memc(tmp_path, fake_memcache):
    gz = make_gz(
        tmp_path,
        "20170929000000.tsv.gz",
        "\n".join([
            "idfa\tid1\t1.0\t2.0\t10,11",
            "gaid\tid2\t3.0\t4.0\t12",
            "idfa\tid3\t5.0\t6.0\t",
            "",
        ]) + "\n",
    )

    device_memc = {"idfa": "127.0.0.1:33013", "gaid": "127.0.0.1:33014", "adid": "x", "dvid": "y"}

    processed, errors = ml.process_file(
        str(gz),
        device_memc,
        dry_run=False,
        workers=2,
        batch_size=2,
        queue_size=10,
        socket_timeout=1.0,
        retry=0,
        retry_backoff=0.0,
    )

    assert processed == 3
    assert errors == 0

    c_idfa = fake_memcache[("127.0.0.1:33013",)]
    c_gaid = fake_memcache[("127.0.0.1:33014",)]

    assert "idfa:id1" in c_idfa.storage
    assert "idfa:id3" in c_idfa.storage
    assert "gaid:id2" in c_gaid.storage


def test_iter_files_chronological_sorts(tmp_path):
    (tmp_path / "20170929000200.tsv.gz").write_text("x")
    (tmp_path / "20170929000000.tsv.gz").write_text("x")
    (tmp_path / "20170929000100.tsv.gz").write_text("x")

    files = ml.iter_files_chronological(str(tmp_path / "*.tsv.gz"))
    assert [Path(f).name for f in files] == [
        "20170929000000.tsv.gz",
        "20170929000100.tsv.gz",
        "20170929000200.tsv.gz",
    ]
