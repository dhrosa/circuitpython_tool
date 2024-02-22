"""Custom `click` parameters."""

import logging
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import click
from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem

from ..hw import Device, FakeDevice, Query, RealDevice
from ..uf2 import Board
from . import distinct_device
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


def query_completion(incomplete: str) -> list[CompletionItem]:
    return [
        CompletionItem(":".join((d.vendor, d.model, d.serial)))
        for d in RealDevice.all()
    ]


class QueryParam(ParamType):
    """Click parameter type for parsing Query arguments."""

    name = "query"

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
            return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return query_completion(incomplete)


class DeviceParam(ParamType):
    def convert(
        self, value: str | Device, param: Parameter | None, context: Context | None
    ) -> Device | None:
        if value is None:
            return None
        if isinstance(value, Device):
            return value
        return distinct_device(Query.parse(value))

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return query_completion(incomplete)


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
