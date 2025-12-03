#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import os
import sys
import uuid
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer

from typing import Any, Literal

from distlib.locators import RedirectHandler

import scoring_api.homework.scoring
# from common import configure_logging



SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

MAX_AGE = 70

config: dict[str, str] = {"LOG_PATHы": "mylog.log",}








def configure_logging(logger_name: str, config_file: dict[str, str], level_name: Literal["info", "error", "exception"] = "info") -> logging.Logger:

    levels = {"info": logging.INFO,
              "error": logging.ERROR,
              "exception": logging.ERROR,
              }

    logger_prime = logging.getLogger(logger_name)
    if logger_prime.handlers:
        return logger_prime
    level = levels.get(level_name, logging.INFO)
    handler: logging.Handler = logging.FileHandler(os.path.join(config_file["LOG_PATH"]), encoding="utf-8") if config_file.get("LOG_PATH") else logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname).1s %(name)s: %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )
    handler.setFormatter(formatter)
    logger_prime.setLevel(level)
    logger_prime.addHandler(handler)
    return logger_prime


logger = configure_logging("api.py", config)


def is_empty(value) -> bool:
    return value in (None, "", [], {}, ())



class Field:
    def __init__(self, required: bool = False, nullable: bool = False) -> None:
        self.required: bool = required
        self.nullable: bool = nullable
        self._attr_name: str | None = None


    def __set_name__(self, owner: type, name: str) -> None:
        self._attr_name: str | None = name


    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self._attr_name)


    def __set__(self, instance, value):
        instance.__dict__[self._attr_name] = value


    def validate(self, value):
        if value is None:
            if self.required:
                logger.exception("Oh shit! I'm sorry! %s is required", self._attr_name)
                raise ValueError("%s is required", self._attr_name)
            return None

        if is_empty(value) and not self.nullable:
            logger.exception("Oh shit! I'm sorry! %s may not be empty", self._attr_name)
            raise ValueError("%s may not be empty", self._attr_name)

        return self._validate_type(value)

    def _validate_type(self, value: Any) -> Any:
        return value


class CharField(Field):
    def _validate_type(self, value: Any) -> Any:
        if not isinstance(value, str):
            logger.exception("Oh shit! I'm sorry! This shit %s must be string", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must be string", self._attr_name)
        return value

class ArgumentsField(Field):
    def _validate_type(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            logger.exception("Oh shit! I'm sorry! This shit %s must be dict", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must be dict", self._attr_name)
        return value



class EmailField(CharField):
    def _validate_type(self, value: Any) -> str:
        value = super()._validate_type(value)
        if "@" not in value:
            logger.exception("Oh shit! I'm sorry! This shit %s must have @ symbol", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must have @ symbol", self._attr_name)
        return value


class PhoneField(Field):
    def _validate_type(self, value: Any) -> str:

        if isinstance(value, (int, float)):
            value = str(int(value))

        if not isinstance(value, str):
            logger.exception("Oh shit! I'm sorry! This shit %s must be string or int", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must be string or int", self._attr_name)

        if len(value) != 11:
            logger.exception("Oh shit! I'm sorry! This shit %s must have 11 digits", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must have 11 digits", self._attr_name)

        if not value.isdigit():
            logger.exception("Oh shit! I'm sorry! This shit %s must contain digits only", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must must digit", self._attr_name)

        if not value.startswith("7"):
            logger.exception("Oh shit! I'm sorry! This shit %s must start with 7", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must star with 7", self._attr_name)

        return value

class DateField(Field):
    date_format = "%d.%m.%Y"

    def _validate_type(self, value: Any) -> datetime.date:
        if not isinstance(value, str):
            logger.exception("Oh shit! I'm sorry! This shit %s must be str", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! This shit %s must be str", self._attr_name)

        try:
            return datetime.datetime.strptime(value, self.date_format).date()
        except ValueError:
            logger.exception("Oh shit! I'm sorry! The %s should be in DD.MM.YYYY format", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! The %s should be in DD.MM.YYYY format", self._attr_name)




class BirthDayField(DateField):
    def _validate_type(self, value: Any) -> datetime.date:
        td = super()._validate_type(value)

        today = datetime.date.today()

        if td > today:
            logger.exception("Oh shit! I'm sorry! The %s can't in the future", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! The %s can't in the future", self._attr_name)

        age = (today - td).days / 265.25
        if age > MAX_AGE:
            logger.exception("Oh shit! I'm sorry! The %s can't is older than %s", self._attr_name, MAX_AGE)
            raise ValueError("Oh shit! I'm sorry! The %s can't is older than %s", self._attr_name, MAX_AGE)

        return td

class GenderField(Field):
    def _validate_type(self, value: Any) -> int:
        if not isinstance(value, int):
            logger.exception("Oh shit! I'm sorry! The %s must be int", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! The %s must be int", self._attr_name)
        if value not in GENDERS:
            logger.exception("Oh shit! I'm sorry! The %s must be one of %s", self._attr_name, list(GENDERS.keys()))
            raise ValueError("Oh shit! I'm sorry! The %s must be int", self._attr_name)
        return value




class ClientIDsField(Field):
    def _validate_type(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            logger.exception("Oh shit! I'm sorry! The %s must be list", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! The %s must be list", self._attr_name)
        if not value:
            logger.exception("Oh shit! I'm sorry! The %s shouldn't be empty", self._attr_name)
            raise ValueError("Oh shit! I'm sorry! The %s shouldn't be empty", self._attr_name)
        for v in value:
            if not isinstance(v, int):
                logger.exception("Oh shit! I'm sorry! The %s contain int", self._attr_name)
                raise ValueError("Oh shit! I'm sorry! The %s contain int", self._attr_name)

        return value


class RequestMeta(type):
    def __new__(mcs, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> "RequestMeta":
        fields: dict[str, Field] = {key: value for key, value in attrs.items() if isinstance(value, Field)}
        attrs["_fields"] = fields
        return super().__new__(mcs, name, bases, attrs)


class Request(metaclass=RequestMeta):

    _fields: dict[str, Field]

    def __init__(self, body: dict[str, Any] | None):
        body = body or {}
        self.errors: dict[str, str] = {}


        for name, field in self._fields.items():
            raw_value = body.get(name)
            try:
                value = field.validate(raw_value)
                setattr(self, name, value)
            except ValueError as e:
                self.errors[name] = str(e)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def non_empty_fields(self):
        return [
            name for name in self._fields if not is_empty(getattr(self, name))
        ]



class ClientsInterestsRequest(Request):

    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


    def validate_pairs(self) -> bool:
        pairs: list[tuple[str, str]] = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("gender", "birthday"),
        ]

        for a, b in pairs:
            if not is_empty(getattr(self, a)) and not is_empty(getattr(self, b)):
                return True
        return False


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode('utf-8')).hexdigest()
    return digest == request.token


def format_errors(errors: dict[str, str]) -> str:
    return "; ".join(f"{key}: {value}" for key, value in errors.items())


def handle_online_score(method_request: MethodRequest, ctx: dict[str, Any], store: Any) -> tuple[Any, int]:
    req = OnlineScoreRequest(method_request.arguments)

    if not req.is_valid:
        return format_errors(req.errors), INVALID_REQUEST


    if not req.validate_pairs():
        logger.error("at least one pair of fields must be present: "
         "(phone & email), (first_name & last_name), (gender & birthday)",)
        return ("at least one pair of fields must be present: "
         "(phone & email), (first_name & last_name), (gender & birthday)"), INVALID_REQUEST


    ctx["has"] = req.non_empty_fields

    if method_request.is_admin:
        score = 42
    else:
        score = scoring_api.homework.scoring.get_score(
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
        method_request: MethodRequest,
        ctx: dict[str, Any],
        store: Any
) -> tuple[Any, int]:
    req = ClientsInterestsRequest(method_request.arguments)

    if not req.is_valid:
        logger.error("Oh shit! I'm sorry! Invalid request %s", format_errors(req.errors))
        return format_errors(req.errors), INVALID_REQUEST

    ctx["nclients"] = len(req.client_ids)

    resp: dict[str, Any] ={}

    for cid in req.client_ids:
        resp[str(cid)] = scoring_api.homework.scoring.get_interests(store, cid)
    return resp, OK






def method_handler(request: dict[str, Any], ctx: dict[str, Any], store: Any) -> tuple[Any, int]:

    body = request.get("body") or {}
    method_req = MethodRequest(body)

    if not method_req.is_valid:
        logger.error("Oh shit! I'm sorry! Invalid request %s", format_errors(method_req.errors))
        return format_errors(method_req.errors), INVALID_REQUEST


    if not check_auth(method_req):
        logger.error("Oh shit! I'm sorry! %s %s", ERRORS[FORBIDDEN], FORBIDDEN)
        return ERRORS[FORBIDDEN], FORBIDDEN


    if method_req.method == "online_score":
        return handle_online_score(method_req, ctx, store)


    if method_req.method == "clients_interests":
        return handle_clients_interests(method_req, ctx, store)

    logger.error("Oh shit! I'm sorry! %s", INVALID_REQUEST)
    return "Unknown method", INVALID_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
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
        context: dict[str, Any] = {"request_id": self.get_request_id(self.headers)}
        request_data: dict[str, Any] | None = None
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


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()



    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()