#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import uuid
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Tuple

from mypy.dmypy.client import request

import scoring


# === Константы из условия ===

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500

ERRORS: Dict[int, str] = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}

UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS: Dict[int, str] = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

MAX_AGE = 70  # макс возраст по условию


def is_empty(value: Any) -> bool:
    """True, если значение считаем 'пустым' (по условию ДЗ)."""
    return value in (None, "", [], {}, ())


# =====================================================================
#                         ДЕСКРИПТОРЫ-ПОЛЯ
# =====================================================================

class Field:
    """
    Базовое поле-дескриптор.

    - required: ключ ОБЯЗАН быть в JSON (если его нет → ошибка).
    - nullable: значение МОЖЕТ быть пустым ("" / null / [] / {}).
    """

    def __init__(self, required: bool = False, nullable: bool = False) -> None:
        self.required: bool = required
        self.nullable: bool = nullable
        # сюда Python положит имя атрибута в классе через __set_name__
        self.name: Optional[str] = None

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Вызывается автоматически при создании класса,
        где это поле объявлено:

            class X(Request):
                email = EmailField()

        Тогда здесь name == "email".
        """
        self.name = name

    def __get__(self, instance: Any, owner: type) -> Any:
        """
        Чтение атрибута:
            obj.email -> попадает сюда.
        """
        if instance is None:
            # доступ через класс: OnlineScoreRequest.email → вернём сам дескриптор
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any) -> None:
        """
        Запись атрибута:
            obj.email = value -> попадает сюда.

        ВАЖНО: здесь НЕТ валидации.
        Валидация делается централизованно в Request.__init__,
        чтобы:
        - иметь список ошибок в одном месте,
        - проверять даже отсутствующие поля (required).
        """
        instance.__dict__[self.name] = value  # type: ignore[index]

    def validate(self, value: Any) -> Any:
        """
        Общая валидация:
        - проверяем required (обязательное поле),
        - проверяем nullable (можно ли пустое),
        - вызываем типовую проверку _validate_type.
        """
        if value is None:
            # ключ отсутствует или value = None
            if self.required:
                raise ValueError(f"{self.name} is required")
            return None

        if is_empty(value) and not self.nullable:
            raise ValueError(f"{self.name} may not be empty")

        return self._validate_type(value)

    def _validate_type(self, value: Any) -> Any:
        """
        Типовая проверка. В базовом поле — ничего.
        Наследники (CharField, EmailField, ...) переопределяют.
        """
        return value


class CharField(Field):
    """Простая строка."""

    def _validate_type(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{self.name} must be a string")
        return value


class EmailField(CharField):
    """Строка с обязательным '@'."""

    def _validate_type(self, value: Any) -> str:
        value = super()._validate_type(value)
        if "@" not in value:
            raise ValueError(f"{self.name} must contain '@'")
        return value


class ArgumentsField(Field):
    """Поле 'arguments' — строго dict."""

    def _validate_type(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{self.name} must be a dict")
        return value


class PhoneField(Field):
    """Телефон: строка/число, 11 цифр, начинается с '7'."""

    def _validate_type(self, value: Any) -> str:
        # допускаем int — приведение к строке
        if isinstance(value, int):
            value = str(value)
        elif isinstance(value, float):
            # поддержка float из JSON/кривых клиентов, приводим к int→str
            value = str(int(value))

        if not isinstance(value, str):
            raise ValueError(f"{self.name} must be string or int")

        if len(value) != 11:
            raise ValueError(f"{self.name} must be 11 digits")

        if not value.isdigit():
            raise ValueError(f"{self.name} must contain digits only")

        if not value.startswith("7"):
            raise ValueError(f"{self.name} must start with '7'")

        return value


class DateField(Field):
    """Дата в формате DD.MM.YYYY, на выходе — datetime.date."""

    date_format = "%d.%m.%Y"

    def _validate_type(self, value: Any) -> datetime.date:
        if not isinstance(value, str):
            raise ValueError(f"{self.name} must be a string in format DD.MM.YYYY")

        try:
            return datetime.datetime.strptime(value, self.date_format).date()
        except ValueError:
            raise ValueError(f"{self.name} must be in format DD.MM.YYYY")


class BirthDayField(DateField):
    """Дата рождения: не в будущем и возраст <= MAX_AGE."""

    def _validate_type(self, value: Any) -> datetime.date:
        # сначала превращаем строку в date, используя базовый DateField
        dt = super()._validate_type(value)

        today = datetime.date.today()
        if dt > today:
            raise ValueError(f"{self.name} cannot be in the future")

        age = (today - dt).days / 365.25
        if age > MAX_AGE:
            raise ValueError(f"{self.name} age must be <= {MAX_AGE}")

        return dt


class GenderField(Field):
    """Пол: 0, 1 или 2."""

    def _validate_type(self, value: Any) -> int:
        if not isinstance(value, int):
            raise ValueError(f"{self.name} must be int")
        if value not in GENDERS:
            raise ValueError(f"{self.name} must be one of {list(GENDERS.keys())}")
        return value


class ClientIDsField(Field):
    """Список client_ids: непустой, только int."""

    def _validate_type(self, value: Any) -> List[int]:
        if not isinstance(value, list):
            raise ValueError(f"{self.name} must be list")
        if not value:
            raise ValueError(f"{self.name} must not be empty")
        for v in value:
            if not isinstance(v, int):
                raise ValueError(f"{self.name} must contain ints")
        return value


# =====================================================================
#                 МЕТАКЛАСС + БАЗОВЫЙ КЛАСС ЗАПРОСА
# =====================================================================

class RequestMeta(type):
    """
    Метакласс: при создании класса собирает все Field в _fields.

    Это даёт нам декларативность:
        class X(Request):
            email = EmailField()
            phone = PhoneField()

    и потом в Request.__init__ мы можем пройтись по self._fields
    и провалидировать всё разом.
    """

    def __new__(
        mcs,
        name: str,
        bases: Tuple[type, ...],
        attrs: Dict[str, Any],
    ) -> "RequestMeta":
        fields: Dict[str, Field] = {
            k: v for k, v in attrs.items()
            if isinstance(v, Field)
        }
        attrs["_fields"] = fields
        return super().__new__(mcs, name, bases, attrs)


class Request(metaclass=RequestMeta):
    """
    Базовый реквест:
    - принимает body: dict (JSON),
    - валидирует все поля, объявленные как Field,
    - складывает ошибки в self.errors.
    """

    _fields: Dict[str, Field]

    def __init__(self, body: Optional[Dict[str, Any]]) -> None:
        body = body or {}
        self.errors: Dict[str, str] = {}

        for name, field in self._fields.items():
            raw_value = body.get(name)
            try:
                # универсальная валидация поля
                value = field.validate(raw_value)
                # записываем через дескриптор (Field.__set__)
                setattr(self, name, value)
            except ValueError as e:
                self.errors[name] = str(e)

    @property
    def is_valid(self) -> bool:
        """Нет ошибок валидации — запрос валиден."""
        return not self.errors

    @property
    def non_empty_fields(self) -> List[str]:
        """
        Список полей, у которых значение непустое.
        Для ctx["has"] в online_score.
        """
        return [
            name for name in self._fields
            if not is_empty(getattr(self, name))
        ]


# =====================================================================
#                          КОНКРЕТНЫЕ ЗАПРОСЫ
# =====================================================================

class ClientsInterestsRequest(Request):
    """
    Аргументы метода clients_interests:
      - client_ids: список int, обязателен, непустой
      - date: дата, опционально
    """
    client_ids = ClientIDsField(required=True)
    date = DateField(nullable=True)


class OnlineScoreRequest(Request):
    """
    Аргументы метода online_score.

    Все поля опциональны, могут быть пустыми, но валидность:
    - все поля по отдельности валидны
    - должна быть заполнена хотя бы одна пара:
        * phone + email
        * first_name + last_name
        * gender + birthday
    """
    first_name = CharField(nullable=True)
    last_name = CharField(nullable=True)
    email = EmailField(nullable=True)
    phone = PhoneField(nullable=True)
    birthday = BirthDayField(nullable=True)
    gender = GenderField(nullable=True)

    def validate_pairs(self) -> bool:
        """Проверка, что есть хотя бы одна 'рабочая' пара полей."""
        pairs = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("gender", "birthday"),
        ]
        for a, b in pairs:
            if not is_empty(getattr(self, a)) and not is_empty(getattr(self, b)):
                return True
        return False


class MethodRequest(Request):
    """
    Верхнеуровневый запрос /method:
      - account: необязательное
      - login: обязательное
      - token: обязательное
      - method: обязательное
      - arguments: обязательное, dict
    """
    account = CharField(nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)  # может быть пустым dict
    method = CharField(required=True)

    @property
    def is_admin(self) -> bool:
        return self.login == ADMIN_LOGIN


# =====================================================================
#                        АВТОРИЗАЦИЯ / УТИЛИТЫ
# =====================================================================

def check_auth(request: MethodRequest) -> bool:
    """
    Проверка авторизации по токену.
    Логика как в шаблоне ДЗ, чтобы тесты совпадали.
    """
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        # в шаблоне было прямо account + login, без or ""
        digest = hashlib.sha512(
            (request.account + request.login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == request.token


def format_errors(errors: Dict[str, str]) -> str:
    """Склеиваем словарь ошибок в строку. Тесты проверяют только len > 0."""
    return "; ".join(f"{k}: {v}" for k, v in errors.items())


# =====================================================================
#                         HANDLERS МЕТОДОВ
# =====================================================================

def handle_online_score(
    method_req: MethodRequest,
    ctx: Dict[str, Any],
    store: Any,
) -> Tuple[Any, int]:
    """
    Реализация метода online_score.

    - парсим аргументы в OnlineScoreRequest
    - валидируем поля
    - проверяем пары
    - кладём ctx["has"]
    - если админ — возвращаем 42
    - иначе — считаем скор через scoring.get_score(...)
    """
    req = OnlineScoreRequest(method_req.arguments)

    if not req.is_valid:
        return format_errors(req.errors), INVALID_REQUEST

    if not req.validate_pairs():
        return ("at least one pair of fields must be present: "
                "(phone & email), (first_name & last_name), (gender & birthday)"), INVALID_REQUEST

    # в контекст кладем список непустых полей — тест ждёт это
    ctx["has"] = req.non_empty_fields

    if method_req.is_admin:
        score = 42
    else:
        score = scoring.get_score(
            store=store,
            phone=req.phone,
            email=req.email,
            birthday=req.birthday,
            gender=req.gender,
            first_name=req.first_name,
            last_name=req.last_name,
        )

    return {"score": score}, OK


def handle_clients_interests(
    method_req: MethodRequest,
    ctx: Dict[str, Any],
    store: Any,
) -> Tuple[Any, int]:
    """
    Реализация метода clients_interests.

    - парсим ClientsInterestsRequest
    - валидируем
    - ctx["nclients"] = количество id'шников
    - ответ: {client_id: [interests]}
    """
    req = ClientsInterestsRequest(method_req.arguments)

    if not req.is_valid:
        return format_errors(req.errors), INVALID_REQUEST

    ctx["nclients"] = len(req.client_ids)

    resp: Dict[str, Any] = {}
    for cid in req.client_ids:
        resp[str(cid)] = scoring.get_interests(store, cid)

    return resp, OK


def method_handler(
    request: Dict[str, Any],
    ctx: Dict[str, Any],
    store: Any,
) -> Tuple[Any, int]:
    """
    Главный обработчик /method, который дергают тесты:

        response, code = method_handler({"body": req, "headers": ...}, ctx, settings)
    """
    body = request.get("body") or {}
    method_req = MethodRequest(body)

    if not method_req.is_valid:
        return format_errors(method_req.errors), INVALID_REQUEST

    if not check_auth(method_req):
        return ERRORS[FORBIDDEN], FORBIDDEN

    if method_req.method == "online_score":
        return handle_online_score(method_req, ctx, store)

    if method_req.method == "clients_interests":
        return handle_clients_interests(method_req, ctx, store)

    return "Unknown method", INVALID_REQUEST


# =====================================================================
#                        HTTP-СЕРВЕР / РОУТИНГ
# =====================================================================

class MainHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP-обработчик, как в шаблоне ДЗ.

    Тесты его не используют напрямую, но это нужно для "боевого" запуска:
        python api.py -p 8080
    """

    router = {
        "method": method_handler
    }
    store: Any = None  # заглушка под хранилище

    def get_request_id(self, headers) -> str:
        """Берём request_id из заголовка или генерим новый."""
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self) -> None:
        response: Any = {}
        code: int = OK
        context: Dict[str, Any] = {"request_id": self.get_request_id(self.headers)}
        request_data: Optional[Dict[str, Any]] = None
        data_string: bytes = b""

        try:
            length = int(self.headers.get("Content-Length", 0))
            data_string = self.rfile.read(length)
            if data_string:
                request_data = json.loads(data_string.decode("utf-8"))
            else:
                code = BAD_REQUEST
        except Exception:
            request_data = None
            code = BAD_REQUEST

        if request_data is not None:
            path = self.path.strip("/")
            logging.info("%s: %s %s", path, data_string, context["request_id"])
            handler = self.router.get(path)
            if handler:
                try:
                    response, code = handler(
                        {"body": request_data, "headers": self.headers},
                        context,
                        self.store,
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s", e)
                    code = INTERNAL_ERROR
                    response = None
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if code in ERRORS:
            resp_body = {"code": code, "error": response or ERRORS[code]}
        else:
            resp_body = {"code": code, "response": response}

        context.update(resp_body)
        logging.info(context)

        self.wfile.write(json.dumps(resp_body).encode("utf-8"))


# =====================================================================
#                            ЗАПУСК СЕРВЕРА
# =====================================================================

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )

    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
