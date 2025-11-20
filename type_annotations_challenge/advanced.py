from _typeshed import SupportsItemAccess
from collections.abc import Buffer, Callable
from typing import Protocol, overload, Any, Self, Generator, Never, Literal, Dict, TypedDict, TypeGuard, Concatenate


def read_buffer(b: Buffer):
    ...


class SingleStringInput(Protocol):
    def __call__(self, name: str) -> None:
        ...


def decorator[T: Callable](message: str) -> Callable[[T], T]:
    ...




class Descriptor:
    @overload
    def __get__(self, instance: None, owner: type) -> Self:
        ...

    @overload
    def __get__(self, instance: Any, owner: type) -> str:
        ...

    def __get__(self, instance: Any, owner: type) -> Self | str:
        ...


class MyClass:
    def __init__(self, x: int) -> None:
        self.x = x


    def copy(self) -> "MyClass":
        copied_object = MyClass(x=self.x)
        return copied_object


def gen() -> Generator[int, str, None]:
    """You don't need to implement it"""
    ...


class Stack[T]:
    def __init__(self) -> None:
        self.items: list[T] = []

    def push(self, item: T) -> None:
        self.items.append(item)

    def pop(self):
        return self.items.pop()


def never_call_me(arg: Never):
    pass


def stop() -> Never:
    while True:
        pass


@overload
def process(response: None) -> None:
    ...


@overload
def process(response: int) -> tuple[int, str]:
    ...


@overload
def process(response: bytes) -> str:
    ...


def process(response: int | bytes | None) -> str | None | tuple[int, str]:
    ...


@overload
def foo(value: Any, flag: Literal[1]) -> int :
    ...
@overload
def foo(value: Any, flag: Literal[2]) -> str :
    ...
@overload
def foo(value: Any, flag: Literal[3]) -> list :
    ...
@overload
def foo[T](value: T, flag) -> T :
    ...

def foo(value: Any, flag: Any) -> Any:
    ...


class Wrap[T, **P]:
    def __init__(self, func: Callable[P, T]) -> None:
        self.func = func

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args, **kwargs)


class SupportsQuack(Protocol):
    def quack(self) -> None:
        ...


type Tree = Dict[str, "Tree"]


def make_object[T](cls: type[T]) -> T:
    ...


class Student(TypedDict):
    name: str
    age: int
    school: str


class Undergraduate(Student):
    major: str


def is_string(value: Any) -> TypeGuard[str]:
    return isinstance(value, str)


class MyContainer(SupportsItemAccess):
    ...


class Array[*Ts]:
    def __add__(self, other: "Array[*Ts]") -> "Array[*Ts]":
        ...


