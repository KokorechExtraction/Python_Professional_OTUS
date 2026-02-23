# Memcache loader (конкурентная версия)

Скрипт читает логи трекера мобильных приложений (`*.tsv.gz`), сериализует данные в protobuf и **конкурентно** заливает их в несколько memcached-инстансов.

## Что делает скрипт

1. Находит входные файлы по маске `--pattern` (по умолчанию `/data/appsinstalled/*.tsv.gz`), сортирует их.
2. Для каждой строки файла:
   - парсит поля: `dev_type`, `dev_id`, `lat`, `lon`, `apps`
   - формирует ключ memcache: `<dev_type>:<dev_id>`
   - формирует protobuf `UserApps` и сериализует в bytes
   - кладёт задачу `(key, packed_bytes)` в очередь **того memcache**, который соответствует `dev_type`
3. Для каждого memcache-адреса запускает `workers_per_addr` потоков-писателей (`MemcacheWorker`), которые:
   - берут задачи из очереди
   - накапливают batch размера `--batch`
   - пишут пачкой через `set_multi()`
   - при ошибках делают retry с backoff
4. После обработки файла переименовывает файл в скрытый (добавляет `.` в начало имени), чтобы не обработать повторно.

## Требования

- Python 3.9+ (желательно)
- memcached (локально или удалённо)
- зависимости:
  - `protobuf` (для `appsinstalled_pb2`)
  - `python-memcached` (пакет `memcache`)

Установка зависимостей (пример):
```bash
pip install protobuf python-memcached
```

## Запуск memcached локально (пример)

Если memcached установлен:
```bash
memcached -p 33013 -d
memcached -p 33014 -d
memcached -p 33015 -d
memcached -p 33016 -d
```

## Запуск скрипта

Пример:
```bash
python memc_load.py --pattern "/data/appsinstalled/*.tsv.gz" \
  --idfa 127.0.0.1:33013 --gaid 127.0.0.1:33014 \
  --adid 127.0.0.1:33015 --dvid 127.0.0.1:33016 \
  --workers 2 --batch 256 --queue-size 50000 \
  --timeout 1.0 --retry 1 --retry-backoff 0.05
```

### Dry-run (не пишет в memcache)

```bash
python memc_load.py --pattern "/data/appsinstalled/*.tsv.gz" --dry
```

В dry-run режиме скрипт:
- не пишет в memcache
- печатает (DEBUG) что *бы* записал

## Аргументы командной строки

- `--pattern` — маска файлов для обработки (glob), например `/data/appsinstalled/*.tsv.gz`
- `--idfa / --gaid / --adid / --dvid` — адреса memcache для соответствующих `dev_type`
- `--workers` — **количество потоков-писателей на каждый memcache-адрес**  
  `0` или не задано → будет `1` (минимум)
- `--batch` — размер пачки для `set_multi()` (сколько key/value отправлять за раз)
- `--queue-size` — максимальный размер очереди задач на **один** memcache-адрес (защита памяти)
- `--timeout` — `socket_timeout` для `python-memcached` (сек)
- `--retry` — сколько раз повторять отправку пачки при исключении
- `--retry-backoff` — базовая задержка между ретраями (сек), умножается на номер попытки
- `-l / --log` — файл логов (если не указан — лог в stdout/stderr)
- `-t / --test` — запустить встроенный protobuf-тест и выйти

## Как работает остановка потоков

После чтения файла в каждую очередь кладутся `None` (sentinel) **по числу воркеров**, обслуживающих эту очередь.  
Воркеры, получив `None`, делают flush оставшегося batch и завершаются.

## Формат входных данных

Каждая строка (TSV) ожидается в формате:

```
<dev_type>\t<dev_id>\t<lat>\t<lon>\t<app1,app2,app3,...>
```

Пример:
```
idfa    1rfw452y52g2gq4g    55.55   42.42   1423,43,567,3,7,23
```

