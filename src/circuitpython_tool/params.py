import pathlib
from typing import Any, Callable, TypeAlias, cast

import click
from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem

from . import completion, fake_device
from .config import ConfigStorage
from .query import Query
from .shared_state import SharedState
from .uf2 import Board


class ConfigStorageParam(click.Path):
    """Click paramter for parsing paths to ConfigStorage.

    We return a paramter value, but also set the corrent context's object to the
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
        devices = fake_device.all_devices(value)
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
        self, value: str | Query, param: Parameter | None, context: Context | None
    ) -> Query:
        if isinstance(value, Query):
            return value
        try:
            if ":" in value:
                return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))
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
        self, value: str | Board, param: Parameter | None, context: Context | None
    ) -> Board:
        if isinstance(value, Board):
            return value
        try:
            board = Board.all()[value]
        except KeyError:
            self.fail(f"Unknown board_id: {value}")
        return board

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return [
            CompletionItem(id) for id in Board.all().keys() if id.startswith(incomplete)
        ]


class LanguageParam(ParamType):
    """Click parameter for CircuitPython language codes."""

    name = "language"

    def convert(
        self, value: str, param: Parameter | None, context: Context | None
    ) -> str:
        languages = Board.all_languages()
        if value in languages:
            return value
        self.fail(f"Invalid language: '{value}'. Valid options: {languages}")

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return [
            CompletionItem(lang)
            for lang in Board.all_languages()
            if lang.startswith(incomplete)
        ]


AnyCallable: TypeAlias = Callable[..., Any]


def label_or_query_argument(
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Callable[[AnyCallable], AnyCallable]:
    """Decorator that accepts a device label or a raw query string, and passes
    an argument of type Query to the command."""

    # The return value will be a Query, likely with the name 'query', but we
    # want to communicate to the user that either a device label or query string
    # works.
    kwargs.setdefault("metavar", "LABEL_OR_QUERY")
    return click.argument(name, *args, type=QueryOrLabelParam(), **kwargs)
