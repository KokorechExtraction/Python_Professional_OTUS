package main

import (
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"google.golang.org/protobuf/proto"
)

const normalErrRate = 0.01

type AppsInstalled struct {
	DevType string
	DevID   string
	Lat     float64
	Lon     float64
	Apps    []uint32
}

type job struct {
	Key   string
	Value []byte
}

type stats struct {
	processed uint64
	errors    uint64
}

type memcacheClient struct {
	addr    string
	timeout time.Duration
}

func newMemcacheClient(addr string, timeout time.Duration) *memcacheClient {
	return &memcacheClient{addr: addr, timeout: timeout}
}

func (c *memcacheClient) SetMulti(items []job) error {
	if len(items) == 0 {
		return nil
	}

	conn, err := net.DialTimeout("tcp", c.addr, c.timeout)
	if err != nil {
		return err
	}
	defer conn.Close()

	if err := conn.SetDeadline(time.Now().Add(c.timeout)); err != nil {
		return err
	}

	reader := bufio.NewReader(conn)
	writer := bufio.NewWriter(conn)

	for _, item := range items {
		if item.Key == "" {
			return errors.New("empty memcache key")
		}
		if _, err := fmt.Fprintf(writer, "set %s 0 0 %d\r\n", item.Key, len(item.Value)); err != nil {
			return err
		}
		if _, err := writer.Write(item.Value); err != nil {
			return err
		}
		if _, err := writer.WriteString("\r\n"); err != nil {
			return err
		}
	}
	if err := writer.Flush(); err != nil {
		return err
	}

	for range items {
		line, err := reader.ReadString('\n')
		if err != nil {
			return err
		}
		line = strings.TrimSpace(line)
		if line != "STORED" {
			return fmt.Errorf("unexpected memcache response: %q", line)
		}
	}

	return nil
}

type worker struct {
	addr         string
	ch           <-chan job
	dryRun       bool
	batchSize    int
	retries      int
	retryBackoff time.Duration
	client       *memcacheClient
	stats        *stats
}

func newWorker(addr string, ch <-chan job, dryRun bool, batchSize, retries int, timeout, retryBackoff time.Duration, s *stats) *worker {
	return &worker{
		addr:         addr,
		ch:           ch,
		dryRun:       dryRun,
		batchSize:    max(1, batchSize),
		retries:      max(0, retries),
		retryBackoff: retryBackoff,
		client:       newMemcacheClient(addr, timeout),
		stats:        s,
	}
}

func (w *worker) run(wg *sync.WaitGroup) {
	defer wg.Done()

	batch := make([]job, 0, w.batchSize)
	flush := func() {
		if len(batch) == 0 {
			return
		}
		w.flush(batch)
		batch = batch[:0]
	}

	for j := range w.ch {
		batch = append(batch, j)
		if len(batch) >= w.batchSize {
			flush()
		}
	}
	flush()
}

func (w *worker) flush(batch []job) {
	if len(batch) == 0 {
		return
	}

	if w.dryRun {
		atomic.AddUint64(&w.stats.processed, uint64(len(batch)))
		return
	}

	var err error
	for attempt := 0; attempt <= w.retries; attempt++ {
		err = w.client.SetMulti(batch)
		if err == nil {
			atomic.AddUint64(&w.stats.processed, uint64(len(batch)))
			return
		}
		log.Printf("ERROR cannot write batch to memcache %s (attempt %d/%d): %v", w.addr, attempt+1, w.retries+1, err)
		if attempt < w.retries {
			time.Sleep(time.Duration(attempt+1) * w.retryBackoff)
		}
	}

	atomic.AddUint64(&w.stats.errors, uint64(len(batch)))
}

func dotRename(path string) error {
	dir, file := filepath.Split(path)
	return os.Rename(path, filepath.Join(dir, "."+file))
}

func iterFilesChronological(pattern string) ([]string, error) {
	files, err := filepath.Glob(pattern)
	if err != nil {
		return nil, err
	}
	sort.Strings(files)
	return files, nil
}

func parseAppsInstalled(line string) (*AppsInstalled, error) {
	parts := strings.Split(strings.TrimSpace(line), "\t")
	if len(parts) < 5 {
		return nil, errors.New("not enough fields")
	}

	devType, devID, latRaw, lonRaw, rawApps := parts[0], parts[1], parts[2], parts[3], parts[4]
	if devType == "" || devID == "" {
		return nil, errors.New("empty device type or id")
	}

	apps := make([]uint32, 0)
	for _, raw := range strings.Split(rawApps, ",") {
		raw = strings.TrimSpace(raw)
		if raw == "" {
			continue
		}
		v, err := strconv.ParseUint(raw, 10, 32)
		if err != nil {
			log.Printf("INFO non-digit app id skipped: %q", raw)
			continue
		}
		apps = append(apps, uint32(v))
	}

	lat, err := strconv.ParseFloat(latRaw, 64)
	if err != nil {
		log.Printf("INFO invalid lat %q", latRaw)
	}
	lon, err2 := strconv.ParseFloat(lonRaw, 64)
	if err2 != nil {
		log.Printf("INFO invalid lon %q", lonRaw)
	}
	if err != nil || err2 != nil {
		lat, lon = 0, 0
	}

	return &AppsInstalled{
		DevType: devType,
		DevID:   devID,
		Lat:     lat,
		Lon:     lon,
		Apps:    apps,
	}, nil
}

func makeKeyAndValue(ai *AppsInstalled) (string, []byte, error) {
	ua := &UserApps{
		Apps: ai.Apps,
		Lat:  ai.Lat,
		Lon:  ai.Lon,
	}
	packed, err := proto.Marshal(ua)
	if err != nil {
		return "", nil, err
	}
	key := ai.DevType + ":" + ai.DevID
	return key, packed, nil
}

func processFile(
	filename string,
	deviceMemc map[string]string,
	dryRun bool,
	workersPerAddr int,
	batchSize int,
	queueSize int,
	timeout time.Duration,
	retries int,
	retryBackoff time.Duration,
) (uint64, uint64) {
	addrsMap := make(map[string]struct{})
	for _, addr := range deviceMemc {
		if addr != "" {
			addrsMap[addr] = struct{}{}
		}
	}
	if len(addrsMap) == 0 {
		log.Printf("ERROR no memcache addresses configured")
		return 0, 0
	}

	addrs := make([]string, 0, len(addrsMap))
	for addr := range addrsMap {
		addrs = append(addrs, addr)
	}
	sort.Strings(addrs)

	if workersPerAddr <= 0 {
		workersPerAddr = 1
	}
	if queueSize <= 0 {
		queueSize = 1
	}

	queues := make(map[string]chan job, len(addrs))
	statsByAddr := make(map[string]*stats, len(addrs))

	var wg sync.WaitGroup
	for _, addr := range addrs {
		queues[addr] = make(chan job, queueSize)
		statsByAddr[addr] = &stats{}
		for i := 0; i < workersPerAddr; i++ {
			wg.Add(1)
			go newWorker(addr, queues[addr], dryRun, batchSize, retries, timeout, retryBackoff, statsByAddr[addr]).run(&wg)
		}
	}

	var parseErrors uint64
	var unknownDeviceErrors uint64

	file, err := os.Open(filename)
	if err != nil {
		log.Printf("ERROR open file %s: %v", filename, err)
		return 0, 1
	}
	defer file.Close()

	gz, err := gzip.NewReader(file)
	if err != nil {
		log.Printf("ERROR create gzip reader for %s: %v", filename, err)
		return 0, 1
	}
	defer gz.Close()

	log.Printf("INFO processing %s", filename)

	reader := bufio.NewReaderSize(gz, 1024*1024)
	for {
		line, err := reader.ReadString('\n')
		if len(line) > 0 {
			line = strings.TrimRight(line, "\r\n")
			if line != "" {
				ai, parseErr := parseAppsInstalled(line)
				if parseErr != nil {
					parseErrors++
				} else {
					addr := deviceMemc[ai.DevType]
					if addr == "" {
						unknownDeviceErrors++
						log.Printf("ERROR unknown device type: %s", ai.DevType)
					} else {
						key, packed, packErr := makeKeyAndValue(ai)
						if packErr != nil {
							parseErrors++
							log.Printf("ERROR protobuf marshal failed for key %s:%s: %v", ai.DevType, ai.DevID, packErr)
						} else {
							if dryRun {
								log.Printf("DEBUG %s - %s -> apps=%d lat=%f lon=%f", addr, key, len(ai.Apps), ai.Lat, ai.Lon)
							}
							queues[addr] <- job{Key: key, Value: packed}
						}
					}
				}
			}
		}

		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			log.Printf("ERROR reading %s: %v", filename, err)
			parseErrors++
			break
		}
	}

	for _, addr := range addrs {
		close(queues[addr])
	}
	wg.Wait()

	var processed uint64
	var writeErrors uint64
	for _, addr := range addrs {
		processed += atomic.LoadUint64(&statsByAddr[addr].processed)
		writeErrors += atomic.LoadUint64(&statsByAddr[addr].errors)
	}

	return processed, parseErrors + unknownDeviceErrors + writeErrors
}

func protoTest() error {
	sample := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\n" +
		"gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424\n"

	for _, line := range strings.Split(strings.TrimSpace(sample), "\n") {
		ai, err := parseAppsInstalled(line)
		if err != nil {
			return err
		}
		_, packed, err := makeKeyAndValue(ai)
		if err != nil {
			return err
		}
		decoded := &UserApps{}
		if err := proto.Unmarshal(packed, decoded); err != nil {
			return err
		}
		if decoded.GetLat() != ai.Lat || decoded.GetLon() != ai.Lon || len(decoded.GetApps()) != len(ai.Apps) {
			return fmt.Errorf("protobuf roundtrip mismatch")
		}
	}
	return nil
}

func main() {
	var (
		test         = flag.Bool("test", false, "run self-test")
		logPath      = flag.String("log", "", "log file path")
		dry          = flag.Bool("dry", false, "dry run")
		pattern      = flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "input glob")
		idfa         = flag.String("idfa", "127.0.0.1:33013", "idfa memcache address")
		gaid         = flag.String("gaid", "127.0.0.1:33014", "gaid memcache address")
		adid         = flag.String("adid", "127.0.0.1:33015", "adid memcache address")
		dvid         = flag.String("dvid", "127.0.0.1:33016", "dvid memcache address")
		workers      = flag.Int("workers", 1, "workers per memcache address")
		batch        = flag.Int("batch", 256, "batch size for memcache SetMulti")
		queueSize    = flag.Int("queue-size", 50000, "channel buffer per memcache address")
		timeout      = flag.Duration("timeout", time.Second, "memcache socket timeout")
		retry        = flag.Int("retry", 1, "retry count for failed batch")
		retryBackoff = flag.Duration("retry-backoff", 50*time.Millisecond, "base delay between retries")
	)
	flag.Parse()

	if *logPath != "" {
		file, err := os.OpenFile(*logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
		if err != nil {
			log.Fatalf("cannot open log file: %v", err)
		}
		defer file.Close()
		log.SetOutput(file)
	}
	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds)

	if *test {
		if err := protoTest(); err != nil {
			log.Fatalf("test failed: %v", err)
		}
		log.Printf("INFO test passed")
		return
	}

	deviceMemc := map[string]string{
		"idfa": *idfa,
		"gaid": *gaid,
		"adid": *adid,
		"dvid": *dvid,
	}

	files, err := iterFilesChronological(*pattern)
	if err != nil {
		log.Fatalf("glob failed: %v", err)
	}
	if len(files) == 0 {
		log.Printf("WARNING no files matched pattern: %s", *pattern)
		return
	}

	for _, fn := range files {
		processed, errs := processFile(fn, deviceMemc, *dry, *workers, *batch, *queueSize, *timeout, *retry, *retryBackoff)
		if processed == 0 {
			if err := dotRename(fn); err != nil {
				log.Printf("ERROR rename %s: %v", fn, err)
			}
			log.Printf("WARNING no records processed, file renamed anyway: %s", fn)
			continue
		}

		errRate := float64(errs) / float64(processed)
		if errRate < normalErrRate {
			log.Printf("INFO acceptable error rate (%f). successful load", errRate)
		} else {
			log.Printf("ERROR high error rate (%f > %f). failed load", errRate, normalErrRate)
		}

		if err := dotRename(fn); err != nil {
			log.Printf("ERROR rename %s: %v", fn, err)
		}
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
