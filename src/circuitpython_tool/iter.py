from collections.abc import Callable, Iterator
from functools import wraps
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


def as_list(f: Callable[P, Iterator[T]]) -> Callable[P, list[T]]:
    """Decorator to transform generator-returnng functions to list-returning functinos."""

    @wraps(f)
    def inner(*args: P.args, **kwargs: P.kwargs) -> list[T]:
        return list(f(*args, **kwargs))

    return inner
