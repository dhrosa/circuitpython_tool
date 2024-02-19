"""Custom `click` parameters."""

import logging
import pathlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeAlias, cast

import click
from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem

from ..hw import FakeDevice, Query
from ..uf2 import Board
from . import completion
from .config import ConfigStorage
from .shared_state import SharedState


@contextmanager
def supressed_logging(context: Context | None = None) -> Iterator[None]:
    if context and not context.resilient_parsing:
        # If resilient parsing isn't explicitly set, we assume we're in a
        # context where logging is okay (e.g. inside one of our click commands).
        yield
        return
    # If there is no context, or resilient parsing is explicitly set, we assume
    # we're in a context where logging may interfere with the program (e.g.
    # shell completion).
    #
    # TODO(dhrosa): We should be able to redirect to STDERR instead.
    logging.disable()
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)


class ConfigStorageParam(click.Path):
    """Click paramter for parsing paths to ConfigStorage.

    We return a parameter value, but also set the corrent context's object to the
    ConfigStorage instance.
    """

    name = "config_file"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["dir_okay"] = False
        kwargs["path_type"] = pathlib.Path
        super().__init__(*args, **kwargs)

    def convert(  # type: ignore[override]
        self,
        value: str | pathlib.Path | ConfigStorage,
        param: Parameter | None,
        context: Context | None,
    ) -> ConfigStorage:
        match value:
            case ConfigStorage():
                storage = value
            case pathlib.Path():
                storage = ConfigStorage(value)
            case _:
                assert param is not None
                assert context is not None
                path = cast(pathlib.Path, super().convert(value, param, context))
                storage = ConfigStorage(path)
        assert context
        state = context.ensure_object(SharedState)
        state.config_storage = storage
        return storage


class FakeDeviceParam(click.Path):
    """Click parameter to setup fake devices for testing and demos."""

    name = "fake_device_config"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["dir_okay"] = False
        kwargs["path_type"] = pathlib.Path
        kwargs["exists"] = True
        super().__init__(*args, **kwargs)

    def convert(  # type: ignore[override]
        self,
        value: str | pathlib.Path | None,
        param: Parameter | None,
        context: Context | None,
    ) -> None:
        match value:
            case str():
                value = pathlib.Path(value)
            case pathlib.Path():
                pass
            case None:
                return

        assert context
        # Eagerly evaluate here to force file errors to happen here.
        devices = FakeDevice.all(value)
        context.ensure_object(SharedState).all_devices = lambda: devices


class QueryParam(ParamType):
    """Click parameter type for parsing Query arguments."""

    name = "query"

    def convert(
        self, value: str, param: Parameter | None, context: Context | None
    ) -> Query:
        try:
            return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return completion.query(context, param, incomplete)


class QueryOrLabelParam(ParamType):
    """Click parameter type for Query arguments, represented by either Query
    syntax or the name of an existing device label."""

    name = "label_or_query"

    def convert(
        self,
        value: str | Query | None,
        param: Parameter | None,
        context: Context | None,
    ) -> Query | None:
        if value is None:
            return None
        if isinstance(value, Query):
            return value
        try:
            if ":" in value:
                return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))
        # TODO(dhrosa): Actually implement device label lookup
        return Query("", "", "")

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return completion.device_label(context, param, incomplete) + completion.query(
            context, param, incomplete
        )


class BoardParam(ParamType):
    """Click paramater for CircuitPython board IDs."""

    name = "board_id"

    def convert(
        self,
        value: str | Board | None,
        param: Parameter | None,
        context: Context | None,
    ) -> Board | None:
        if value is None:
            return None
        if isinstance(value, Board):
            return value
        with supressed_logging(context):
            boards = Board.all()
        for board in boards:
            if board.id == value:
                return board
        self.fail(f"Unknown board_id: {value}")

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        with supressed_logging():
            boards = Board.all()
        return [CompletionItem(b.id) for b in boards if b.id.startswith(incomplete)]


class LocaleParam(ParamType):
    """Click parameter for CircuitPython locale codes."""

    name = "locale"

    def convert(
        self, value: str | None, param: Parameter | None, context: Context | None
    ) -> str | None:
        if value is None:
            return None
        with supressed_logging(context):
            locales = Board.all_locales()
        if value in locales:
            return value
        self.fail(f"Invalid locale: '{value}'. Valid options: {locales}")

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        with supressed_logging(context):
            locales = Board.all_locales()
        return [CompletionItem(lang) for lang in locales if lang.startswith(incomplete)]


AnyCallable: TypeAlias = Callable[..., Any]


def label_or_query_argument(
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Callable[[AnyCallable], AnyCallable]:
    """Decorator that accepts a device label or a raw query string, and passes
    an argument of type Query to the command."""

    kwargs.setdefault("required", False)
    # The return value will be a Query, likely with the name 'query', but we
    # want to communicate to the user that either a device label or query string
    # works.
    metavar = "LABEL_OR_QUERY"
    if not kwargs.get("required"):
        metavar = f"[{metavar}]"
    kwargs.setdefault("metavar", metavar)
    return click.argument(name, *args, type=QueryOrLabelParam(), **kwargs)
