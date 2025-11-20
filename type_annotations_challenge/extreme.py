from collections.abc import Sequence
from typing import Callable, Concatenate, Any


class Person:
    pass


def transform[T, **P](f: Callable[[Concatenate[Any, P]], T]):
    def wrapper(value: Person, *args: P.args, **kwargs: P.kwargs) -> T:
        return f(value, *args, **kwargs)

    return wrapper


def constructor_parameter[**P, T, R](
    cls: Callable[P, T],
) -> Callable[[Callable[[T], R]], Callable[P, R]]:
    ...


class Fn[R, **P]:
    def __init__(self, f: Callable[P, R]) -> None:
        self.f = f

    def transform_callable(self) -> Callable[[Concatenate[Any, P]], R]:
        ...


def f(a: list[int | str]):
    pass


def g(a: Sequence[int | str]):
    pass