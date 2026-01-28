# FastAPI + ONNX inference + JWT + RBAC (homework)

## Что лежит в папке
- `main.py` — сервис FastAPI с JWT и RBAC
- `requirements.txt` — зависимости
- `Dockerfile` — сборка образа
- `docker-compose.yml` — запуск через compose
- `.env.example` — пример env (скопировать в `.env`)

## Важно про ONNX модель
Код ожидает файл модели рядом с `main.py`:
- `diabetes_model.onnx`



## Запуск локально (без Docker)
```bash
pip install -r requirements.txt
cp .env.example .env

uvicorn main:app --reload
```
Swagger:
- http://localhost:8000/docs

## Запуск в Docker Compose
```bash
cp .env.example .env

docker compose up --build
```
Swagger:
- http://localhost:8000/docs
