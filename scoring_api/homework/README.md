### Scoring API

Небольшое HTTP API для скоринга пользователей и получения интересов клиентов.  
Сервис принимает **POST JSON** на эндпойнт `/method` и в зависимости от поля `method` выполняет один из двух сценариев:

- `online_score` — расчёт скоринга пользователя  
- `clients_interests` — получение интересов по списку client_id  

---

### Структура проекта

Основной файл API:

```
api.py
```

Используются:

- дескрипторы (`Field`, `CharField`, `EmailField`, `PhoneField`, и др.) для типовой валидации полей  
- метакласс `RequestMeta` для декларативного описания запросов (`OnlineScoreRequest`, `ClientsInterestsRequest`, `MethodRequest`)  
- модуль `scoring_api.homework.scoring`:
  - `get_score(store, ...)`
  - `get_interests(store, client_id)`

---

### Как запустить сервер

```
python api.py -p 8080
```

Параметры:

- `-p / --port` — порт (по умолчанию `8080`)
- `-l / --log` — путь к лог-файлу (при отсутствии — лог в stdout)

После запуска сервер слушает:

```
POST http://localhost:<port>/method
```

---

### Формат запроса

Все запросы — `POST /method` с JSON:

```
{
  "account": "<имя компании>",
  "login": "<имя пользователя>",
  "method": "<имя метода>",
  "token": "<токен>",
  "arguments": { ... }
}
```

Поля:

- `account` — строка, опционально  
- `login` — строка, обязательно  
- `method` — строка, обязательно  
- `token` — строка, обязательно  
- `arguments` — dict, обязательно  

При ошибке верхнеуровневой валидации возвращается:

```
422 Invalid Request
```

---

### Формат ответа

Успешный ответ:

```
{
  "code": 200,
  "response": { ... }
}
```

Ответ с ошибкой:

```
{
  "code": <число>,
  "error": "<описание ошибки>"
}
```

Коды:

- `200 OK`
- `400 Bad Request`
- `403 Forbidden`
- `404 Not Found`
- `422 Invalid Request`
- `500 Internal Server Error`

---

### Аутентификация

Функция:

```
check_auth(request)
```

Правила:

- если `login == "admin"`:
  ```
  token = sha512(YYYYMMDDHH + ADMIN_SALT)
  ```
- иначе:
  ```
  token = sha512(account + login + SALT)
  ```

При ошибке → `403 Forbidden`.

---

### Метод: online_score

#### Аргументы

```
{
  "phone": "7917...",        // str или int, 11 цифр, начинается с 7
  "email": "mail@domain",    // должен содержать @
  "first_name": "Имя",
  "last_name": "Фамилия",
  "birthday": "DD.MM.YYYY",
  "gender": 0|1|2
}
```

Все аргументы опциональны, но должна быть заполнена **хотя бы одна пара**:

- phone + email  
- first_name + last_name  
- gender + birthday  

При отсутствии пары → `422`.

#### Контекст

```
ctx["has"] = список непустых полей
```

#### Ответ

Для обычного пользователя:

```
{"score": <число>}
```

Админ всегда получает:

```
{"score": 42}
```

---

### Метод: clients_interests

#### Аргументы

```
{
  "client_ids": [1,2,3],   // список int, обязателен и не пуст
  "date": "DD.MM.YYYY"
}
```

#### Контекст

```
ctx["nclients"] = len(client_ids)
```

#### Ответ

```
{
  "1": ["interest1", "interest2"],
  "2": ["interestX"]
}
```

Интересы берутся:

```
get_interests(store, client_id)
```

---

### Логирование

Используется:

```
configure_logging(...)
```

Формат:

```
[YYYY.MM.DD HH:MM:SS] <LEVEL> api.py: <message>
```

Лог-файл определяется `config["LOG_PATH"]`, иначе stdout.

---

### Как запустить тесты

```
python test.py
```

или:

```
python -m unittest test.py
pytest test.py
```

Ожидается: **все тесты проходят (8 passed)**.

---

### Примеры запросов

#### online_score

```
curl -X POST -H "Content-Type: application/json"   -d '{
        "account": "horns&hoofs",
        "login": "h&f",
        "method": "online_score",
        "token": "<валидный_токен>",
        "arguments": {
          "phone": "79175002040",
          "email": "stupnikov@otus.ru",
          "first_name": "Имя",
          "last_name": "Фамилия",
          "birthday": "01.01.1990",
          "gender": 1
        }
      }'   http://127.0.0.1:8080/method
```

#### clients_interests

```
curl -X POST -H "Content-Type: application/json"   -d '{
        "account": "horns&hoofs",
        "login": "admin",
        "method": "clients_interests",
        "token": "<валидный_токен>",
        "arguments": {
          "client_ids": [1, 2, 3],
          "date": "20.07.2017"
        }
      }'   http://127.0.0.1:8080/method
```
