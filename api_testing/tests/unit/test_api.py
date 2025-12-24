import pytest
from typing import Any
from collections.abc import Callable
from api_testing import api
from api_testing.tests.conftest import FakeStore


def make_request(
        *,
        account: str,
        login: str,
        token: str,
        method: str,
        arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "account": account,
        "login": login,
        "token": token,
        "method": method,
        "arguments": arguments,
    }


def test_empty_request_returns_invalid_request(
        call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
) -> None:
    response, code = call_method({}, FakeStore())
    assert code == api.INVALID_REQUEST


@pytest.mark.parametrize(
    "req",
    [
        {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "token": "",
            "arguments": {},
        },
        {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "token": "bad",
            "arguments": {},
        },
        {
            "account": "",
            "login": api.ADMIN_LOGIN,
            "method": "online_score",
            "token": "",
            "arguments": {},
        },
    ],
    ids=[
        "user_empty_token",
        "user_bad_token",
        "admin_empty_token",
    ],
)
def test_bad_auth_returns_forbidden(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    req: dict[str, Any],
) -> None:
    response, code = call_method(req, FakeStore())
    assert code == api.FORBIDDEN
    assert response == api.ERRORS[api.FORBIDDEN]


def test_admin_online_score_is_42(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    admin_token: str,
) -> None:
    req = make_request(
        account="",
        login=api.ADMIN_LOGIN,
        token=admin_token,
        method="online_score",
        arguments={"phone": "71234567890", "email": "a@b.ru"},
    )
    response, code = call_method(req, FakeStore())
    assert code == api.OK
    assert isinstance(response, dict)
    assert response["score"] == 42


def test_user_online_score_ok(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    user_token: str,
) -> None:
    req = make_request(
        account="acc",
        login="user",
        token=user_token,
        method="online_score",
        arguments={
            "phone": "71234567890",
            "email": "a@b.ru",
        },
    )
    store = FakeStore()  #
    response, code = call_method(req, store)
    assert code == api.OK
    assert "score" in response
    assert isinstance(response["score"], (int, float))




def test_online_score_requires_at_least_one_pair(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    user_token: str,
) -> None:
    req = make_request(
        account="acc",
        login="user",
        token=user_token,
        method="online_score",
        arguments={
            "first_name": "Ivan",

        },
    )
    response, code = call_method(req, FakeStore())
    assert code == api.INVALID_REQUEST
    assert isinstance(response, str)




def test_clients_interests_ok(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    user_token: str,
) -> None:
    store = FakeStore(
        data={
            "i:1": '["cars", "pets"]',
            "i:2": '["travel"]',
        }
    )
    req = make_request(
        account="acc",
        login="user",
        token=user_token,
        method="clients_interests",
        arguments={"client_ids": [1, 2]},
    )
    response, code = call_method(req, store)
    assert code == api.OK
    assert response["1"] == ["cars", "pets"]
    assert response["2"] == ["travel"]




def test_clients_interests_store_failure_returns_error(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    user_token: str,
) -> None:
    store = FakeStore(fail_get=True)
    req = make_request(
        account="acc",
        login="user",
        token=user_token,
        method="clients_interests",
        arguments={"client_ids": [1]},
    )

    with pytest.raises(RuntimeError):
        call_method(req, store)



def test_online_score_cache_failure_still_ok(
    call_method: Callable[[dict[str, Any], Any], tuple[Any, int]],
    user_token: str,  # 123) токен
) -> None:
    store = FakeStore(fail_cache=True)
    req = make_request(
        account="acc",
        login="user",
        token=user_token,
        method="online_score",
        arguments={"phone": "71234567890", "email": "a@b.ru"},
    )


    response, code = call_method(req, store)
    assert code == api.OK
    assert "score" in response


