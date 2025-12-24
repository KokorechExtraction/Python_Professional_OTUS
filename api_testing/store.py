import time
import logging

from collections.abc import Callable
from typing import Any

import redis

logger = logging.getLogger(__name__)

class Store:
    def __init__(
            self,
            host: str = "localhost",
            port: int = 6379,
            db: int = 0,
            timeout: float = 1.0,
            retries: int = 3,
    ) -> None:

        self.host = host
        self.port  = port
        self.db = db
        self.timeout = timeout
        self.retries = retries

        self._client: redis.Redis | None = None


    def _connect(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout,
                decode_responses=True,
            )
        return self._client


    def _with_retry(
            self,
            func: Callable[[redis.Redis], Any],
            *,
            soft: bool = False,
    ) -> Any:

        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                client: redis.Redis = self._connect()
                return func(client)
            except Exception as exc:
                logger.exception(
                    "Oh shit! I'm sorry! Store error (attempt %d/%d): %s",
                    attempt + 1,
                    self.retries,
                    exc,
                )
                self._client = None
                last_exc = exc
                time.sleep(0.1)

        if soft:
            return None
        raise last_exc


    def cache_get(self, key: str) -> str | None:
        return self._with_retry(
            lambda client: client.get(key),
            soft=True,
        )


    def cache_set(self, key: str, score: Any, ttl: int,) -> None:
        return self._with_retry(
            lambda client: client.setex(key, score, ttl),
            soft=True,
        )


    def get(self, key: str) -> str | None:
        return self._with_retry(
            lambda client: client.get(key),
            soft=False,
        )

