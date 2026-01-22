# Django Blog (OTUS Homework)

Учебный проект блога на Django, выполненный по официальному Django Tutorial и приведённый к production-ready виду с применением базовых best practices и принципов 12-factor app.

---

## Стек

* Python 3.13
* Django 6.x
* PostgreSQL
* Docker / docker-compose
* pytest / pytest-django
* gunicorn
* dj-database-url

---

## Функциональность

* CRUD для постов
* Теги
* Счётчик просмотров
* Шаблоны
* Тесты (models / forms / views / crud)
* Docker-окружение
* Конфигурация через переменные окружения

---

## Структура проекта

```
django_blog_fixed/
├── blog/
│   ├── migrations/
│   ├── templates/
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_forms.py
│   │   ├── test_views.py
│   │   └── test_crud.py
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
│
├── django_blog/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── docker-build/
│   └── blog/
│       └── Dockerfile
│
├── docker-compose.yml
├── manage.py
├── pytest.ini
├── pyproject.toml
├── .env
└── README.md
```

---

## Переменные окружения

Пример `.env`:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://postgres:postgres@db:5432/blog

DJANGO_LOG_LEVEL=INFO
```

---

## Запуск локально (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Открыть: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Запуск через Docker

Сборка и запуск:

```bash
docker compose up --build
```

Остановка:

```bash
docker compose down -v
```

---

## База данных

* PostgreSQL используется в Docker / production
* SQLite используется автоматически в тестах

---

## Тесты

Запуск через Django:

```bash
python manage.py test
```

Запуск через pytest:

```bash
pytest
```

`pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = django_blog.settings
python_files = test_*.py
```

---

## Покрытие тестами

* models: создание постов, связи, теги
* forms: валидация формы
* views: list / detail / views counter
* crud: создание поста через HTTP

---

## 12-factor app (применённое)

* конфигурация через env
* разделение кода и конфигурации
* логирование в stdout
* stateless-приложение
* изоляция окружений (local / test / docker)

---

## Назначение проекта

Учебный проект в рамках домашнего задания:

* пройти Django tutorial
* реализовать блог
* покрыть код тестами
* привести проект к production-подобному состоянию
