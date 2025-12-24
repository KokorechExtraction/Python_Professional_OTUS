import hashlib
import datetime
from functools import cache
from typing import Any
import logging
import pytest

from api_testing import api

logger = logging.getLogger(__name__)

class FakeStore():
    def __init__(
            self,
            *,
            cache: dict[str, Any] | None = None,
            data: dict[str, Any] | None = None,
            fail_cache: bool = False,
            fail_get: bool = False,

) -> None:
        self.cache = cache or {}
        self.data = data or {}
        self.fail_cache = fail_cache
        self.fail_get = fail_get


    def cache_get(self, key: str) -> Any:
        if self.fail_cache:
            logger.error("London bridge and cache has fallen down")
            return None
        return self.cache.get(key)


    def cache_set(self, key: str, score: str, ttl: int) -> Any:
        if self.fail_cache:
            logger.error("London bridge and cache has fallen down")
            return
        self.cache[key] = score


    def get(self, key: str) -> Any:
        if self.fail_get:
            logger.error("London bridge and store has fallen down")
            raise RuntimeError("London bridge and store has fallen down")
        return self.data.get(key)




@pytest.fixture()
def user_token() -> str:
    account: str = "acc"
    login: str = "user"
    raw = (account + login + api.SALT).encode('utf-8')
    return hashlib.sha512(raw).hexdigest()


@pytest.fixture()
def admin_token() -> str:
    raw = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode("utf-8")
    return hashlib.sha512(raw).hexdigest()


@pytest.fixture()
def ctx() -> dict[str, Any]:
    return {}


@pytest.fixture()
def headers() -> dict[str, Any]:
    return {}


@pytest.fixture()
def call_method(ctx: dict[str, Any], headers: dict[str, Any]):
    def _call(body: dict[str, Any], store: Any) -> tuple[Any, int]:
        return api.method_handler({"body": body, "headers": headers}, ctx, store)
    return _call