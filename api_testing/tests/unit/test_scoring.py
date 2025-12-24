import hashlib
import datetime
from typing import Any
import pytest
from api_testing import scoring

from api_testing.tests.conftest import FakeStore



def _make_cache_key(
    *,
    first_name: str | None,
    last_name: str | None,
    phone: str | None,
    birthday: datetime.date | None,
) -> str:

    key_parts: list[str] = [
        first_name or "",
        last_name or "",
        phone or "",
        birthday.strftime("%Y%m%d") if birthday else "",
    ]
    raw: str = "".join(key_parts)
    md5: str = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return "uid:" + md5


def test_get_score_returns_cached_value_when_present() -> None:

    birthday: datetime.date = datetime.date(2000, 1, 1)

    key: str = _make_cache_key(
        first_name="Ivan",
        last_name="Petrov",
        phone="71234567890",
        birthday=birthday,
    )


    store: FakeStore = FakeStore(cache={key: 10})


    result: float = scoring.get_score(
        store=store,
        phone="71234567890",
        email=None,
        birthday=birthday,
        gender=None,
        first_name="Ivan",
        last_name="Petrov",
    )


    assert result == 10.0


def test_get_score_calculates_and_puts_into_cache_when_missing() -> None:

    store: FakeStore = FakeStore()


    result: float = scoring.get_score(
        store=store,
        phone="71234567890",  # +1.5
        email="a@b.ru",       # +1.5
        birthday=None,        # не даём пару gender+birthday
        gender=None,
        first_name=None,      # не даём пару first+last
        last_name=None,
    )


    assert result == 3.0


    key: str = _make_cache_key(
        first_name=None,
        last_name=None,
        phone="71234567890",
        birthday=None,
    )


    assert store.cache.get(key) == 3.0


def test_get_score_cache_failure_still_returns_score() -> None:

    store: FakeStore = FakeStore(fail_cache=True)


    result: float = scoring.get_score(
        store=store,
        phone="71234567890",  # +1.5
        email="a@b.ru",       # +1.5
        birthday=None,
        gender=None,
        first_name=None,
        last_name=None,
    )


    assert result == 3.0


def test_get_interests_returns_list_from_store() -> None:

    store: FakeStore = FakeStore(data={"i:1": '["cars", "pets"]'})


    result: list[Any] = scoring.get_interests(store, "1")


    assert result == ["cars", "pets"]


def test_get_interests_raises_when_store_is_down() -> None:

    store: FakeStore = FakeStore(fail_get=True)


    with pytest.raises(RuntimeError):
        scoring.get_interests(store, "1")
