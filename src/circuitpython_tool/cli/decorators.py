from collections.abc import Callable
from functools import wraps
from platform import system
from sys import exit
from typing import ParamSpec, TypeVar

import rich_click as click

from .shared_state import SharedState

pass_shared_state = click.make_pass_decorator(SharedState, ensure=True)
"""Decorator for passing SharedState to a function."""

P = ParamSpec("P")
R = TypeVar("R")


def linux_only(f: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to make a command cleanly exit with an error if not run on Linux.

    This is better than the alternative of crashes in deeper less obvious code locations.
    """

    @wraps(f)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        if system() != "Linux":
            exit("This command is only supported on Linux currently.")
        return f(*args, **kwargs)

    return inner
