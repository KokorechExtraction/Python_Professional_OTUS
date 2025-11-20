from typing import Awaitable, Literal, LiteralString, Iterable, Self, TypedDict, Required, NotRequired, Unpack
from collections.abc import Callable
from typing import ClassVar

def run_async_awaitable(x: Awaitable[int]):
    ...


SingleStringInput_Callable = Callable[[str], None]




class FooClassVar:
    bar: ClassVar[int]


def decorator[T: Callable](func: T) -> T:
    return func


def foo_empty_tuple(x: tuple[()]):
    pass


def add_generic[T](a: T, b: T) -> T:
    ...


def add_generic2[T: (str, int)](a: T, b: T) -> T:
    ...


def add_generic3[T: int](a: T) -> T:
    ...


class FooInstanceVar:
    bar: int


def foo_literal(direction: Literal['left', 'right']):
    ...


def execute_query(sql: LiteralString, parameters: Iterable[str] = ...):
    ...


class Foo:
    def return_self(self) -> Self:
        ...



class Student(TypedDict):
    name: str
    age: int
    school: str


class Student2(TypedDict):
    name: Required[str]
    age: Required[int]
    school: NotRequired[str]


class Person(TypedDict, total=False):
    name: Required[str]
    age:int
    gender: str
    address: str
    email: str


class Person2(TypedDict):
    name: str
    age: int


def foo(**kwargs: Unpack[Person]):
    ...


