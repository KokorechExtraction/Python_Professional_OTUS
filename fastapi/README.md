# ML Model Serving (FastAPI + ONNXRuntime)

Учебный REST API‑сервис для инференса ONNX‑модели **diabetes_model.onnx** через **FastAPI**.

Модель принимает 4 признака пациента:
- **Pregnancies** — количество беременностей  
- **Glucose** — уровень глюкозы  
- **BMI** — индекс массы тела  
- **Age** — возраст  

Модель возвращает вероятность диабета.  
Правило классификации: если **probability > 0.5** → **prediction = 1**, иначе **prediction = 0**.

---

## Что нужно по заданию

✅ `GET /` — приветствие (публично)  
✅ `POST /predict` — принимает JSON с признаками, делает инференс через `onnxruntime`, возвращает `{"prediction": 0|1}`  
✅ Защита `/predict` через **Basic Auth** (логин/пароль)

---

## Требования

- Python 3.10+ (или 3.11)
- Файл модели: `diabetes_model.onnx` в корне проекта
- Зависимости из `requirements.txt`

---

## Структура проекта

Рекомендуемая структура:

```
project/
 ├─ app/
 │   └─ main.py
 ├─ diabetes_model.onnx
 ├─ requirements.txt
 ├─ Dockerfile
 └─ README.md
```

---

## Установка и запуск локально

### 1) Установить зависимости

```bash
pip install -r requirements.txt
```

### 2) Запустить сервис

```bash
uvicorn app.main:app --reload
```

Сервис будет доступен по адресу:
- http://127.0.0.1:8000/

Swagger (UI для тестов):
- http://127.0.0.1:8000/docs

---

## API

### 1) `GET /` (публично)

Проверка, что сервис жив.

```bash
curl http://127.0.0.1:8000/
```

Пример ответа:

```json
{"message":"Hello! This is an ONNX ML inference service."}
```

---

### 2) `POST /predict` (защищено Basic Auth)

**Требует логин/пароль.**  
Тело запроса (JSON):

```json
{
  "Pregnancies": 2,
  "Glucose": 140,
  "BMI": 35.5,
  "Age": 32
}
```

Ответ:

```json
{"prediction": 1}
```

---

## Авторизация (Basic Auth)

В учебном варианте (как на лекции) используются креды:

- **username:** `demo_user`  
- **password:** `demo_pass`

Запрос с авторизацией через curl:

```bash
curl -u demo_user:demo_pass   -H "Content-Type: application/json"   -X POST http://127.0.0.1:8000/predict   -d '{"Pregnancies":2,"Glucose":140,"BMI":35.5,"Age":32}'
```

---

## Docker

### 1) Сборка образа

Из корня проекта:

```bash
docker build -t diabetes-api .
```

### 2) Запуск контейнера

```bash
docker run --rm -p 8000:8000 diabetes-api
```

Проверка:

```bash
curl http://127.0.0.1:8000/
```

---

## Проверка через Swagger

1) Открой: `http://127.0.0.1:8000/docs`  
2) Нажми **Authorize**  
3) Введи `demo_user / demo_pass`  
4) Вызови `POST /predict`

---

## Частые ошибки и решения

### Ошибка: модель не найдена
Проверь, что файл `diabetes_model.onnx` лежит в корне проекта (или путь в коде совпадает).

### Ошибка: неверная форма/тип входа
Чаще всего табличные модели ждут:
- форма: **(1, 4)** — одна строка, 4 признака
- тип: **float32**

### Ошибка 401 на `/predict`
Нужно передать Basic Auth (`-u user:pass`) и убедиться, что логин/пароль верные.

### Ошибка 422 (Unprocessable Entity)
Значит входной JSON не прошёл валидацию: не хватает поля или тип не тот.

---
