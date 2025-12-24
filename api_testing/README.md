### Scoring API — Tests

Репозиторий содержит реализацию HTTP API сервиса скоринга и набор unit-тестов,
написанных с использованием pytest, в рамках домашнего задания OTUS.


### Стек

- Python 3.10+
- pytest
- pytest-cov
- Redis (используется в Store, в тестах заменён FakeStore)


### Установка зависимостей (uv)

Установка dev-зависимостей:

uv add --dev pytest pytest-cov ruff mypy


### Запуск тестов

Запуск всех тестов:

uv run pytest

Запуск с покрытием:

uv run pytest --cov=api_testing --cov-report=term-missing


### Структура проекта

api_testing/
├── api.py                # HTTP API и бизнес-логика
├── scoring.py            # Функции расчёта скоринга и интересов
├── store.py              # Redis Store с retry-логикой
└── tests/
    ├── conftest.py       # Общие pytest-фикстуры и FakeStore
    └── unit/
        ├── test_api.py   # Unit-тесты API
        └── test_scoring.py # Unit-тесты scoring


### FakeStore

В unit-тестах вместо реального Redis используется FakeStore,
реализованный в conftest.py.

FakeStore позволяет:
- эмулировать кэш (cache_get, cache_set)
- эмулировать постоянное хранилище (get)
- проверять поведение системы при падении кэша или store

Это позволяет тестировать бизнес-логику изолированно,
без внешних зависимостей.


### Параметризация тест-кейсов (cases)

Требование задания:

Обязательно необходимо реализовать через декоратор функционал запуска кейса
с разными тест-векторами (либо через фикстуры в pytest),
так чтобы при падении теста было ясно, какой кейс упал.

В проекте используется стандартный механизм pytest —
pytest.mark.parametrize с указанием ids.

Пример:

@pytest.mark.parametrize(
    "req",
    [
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "bad", "arguments": {}},
        {"account": "", "login": api.ADMIN_LOGIN, "method": "online_score", "token": "", "arguments": {}},
    ],
    ids=[
        "user_empty_token",
        "user_bad_token",
        "admin_empty_token",
    ],
)
def test_bad_auth_returns_forbidden(...):
    ...


Использование ids гарантирует, что при падении теста pytest явно показывает,
какой именно кейс не прошёл (например: user_bad_token).

Данный подход является допустимой и рекомендованной альтернативой
самописному декоратору cases, приведённому в условии задания.


### Интеграционные тесты

Интеграционные тесты с реальным Redis являются частью задания со «звёздочкой»
и в данном решении не реализованы.


### Итог

- Реализованы unit-тесты API и scoring
- Используется pytest с параметризацией тест-кейсов
- Обеспечена читаемость упавших кейсов
- Store и внешние зависимости изолированы через FakeStore
