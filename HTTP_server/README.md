# HTTP сервер

Архитектура: **thread pool** (пул потоков): один `accept()`-цикл + N потоков-воркеров, каждый обрабатывает одно соединение.

## Возможности

- `GET` и `HEAD`:
  - `200 OK` — файл найден и доступен
  - `404 Not Found` — файла нет
  - `403 Forbidden` — выход за `DOCUMENT_ROOT`, нет прав/не файл/директория
- Любые другие методы → `405 Method Not Allowed` + `Allow: GET, HEAD`
- `/dir/` → `DOCUMENT_ROOT/dir/index.html`
- Поддержка `%XX` и пробелов в URL (через `unquote`)
- Заголовки: `Date`, `Server`, `Content-Length`, `Content-Type`, `Connection`

## Запуск

```bash
python3 httpd.py -r ./httptest -p 8080 -t 64
```

## Нагрузочный тест (как в задании)

```bash
ab -n 50000 -c 100 -r http://localhost:8080/
```

## Как парсится запрос

1. Читаем из TCP до `\r\n\r\n` (конец header section).
2. Берём первую строку: `METHOD PATH VERSION`.
3. Преобразуем URL в путь на диске внутри `DOCUMENT_ROOT`.
4. Формируем ответ: status line + headers + пустая строка + (тело для GET).
