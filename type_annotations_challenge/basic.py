"""
TODO:

Modify `foo` so it takes an argument of arbitrary type.
"""

from typing import Any
from typing import Final


my_list: Final = []
def foo_any(shit: Any) -> Any:
    pass


def foo_dict(x: dict[str, str]) -> None:
    pass



my_list: Final = []


def foo_kwargs(**kwargs: int | str) -> None:
    ...


def foo_list(x: list[str]) -> None:
    pass


def foo_opt(x: int | None = 69):
    pass


def foo_parameter(x: int):
    pass


def foo_return() -> int:
    return 1

def foo_tuple(x: tuple[str, int]):
    pass

type Vector = list[float]


def foo_union(x: int | str):
    pass


a_variable: int

