"""Library for rendering objects with Rich."""

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any, Protocol, TypeAlias, TypeVar, cast

from humanize import naturaltime
from rich.console import RenderableType
from rich.protocol import is_renderable
from rich.table import Table

TableFieldGetter: TypeAlias = Callable[[Any], Any]
TableField: TypeAlias = tuple[str, TableFieldGetter]
TableFields: TypeAlias = Iterable[TableField]


class TableRenderable(Protocol):
    """Protocol for pretty printing objects using Rich tables."""

    @classmethod
    def __table_fields__(cls) -> TableFields:
        """Specifies fields to render in table output for each instance.

        Each field is specified as a tuple of (field label, getter). `getter` is
        a callable that takes an item instance and returns the value to render.
        """
        ...


def to_table(
    element_type: type[TableRenderable], items: Iterable[TableRenderable]
) -> Table:
    """Render `items` into a table, with each row corresponding to one item.

    Each item must be of type `element_type`.
    """

    labels, getters = zip(*element_type.__table_fields__())

    table = Table()
    for label in labels:
        table.add_column(label, overflow="fold")

    for item in items:
        row = [_to_renderable(getter(item)) for getter in getters]
        table.add_row(*row)

    return table


def to_table_single(item: TableRenderable) -> Table:
    """Render a single object as a table of key-value pairs."""
    table = Table("Property", "Value")
    for label, getter in item.__table_fields__():
        table.add_row(label, _to_renderable(getter(item)))
    return table


def pretty_datetime(timestamp: datetime) -> str:
    """Human-readable rendering of a timestamp and its delta from now."""
    delta = naturaltime(datetime.now() - timestamp)
    return f"{timestamp:%x %X} ({delta})"


def _to_renderable(value: Any) -> RenderableType:
    if is_renderable(value):
        return cast(RenderableType, value)
    return str(value)


T = TypeVar("T", bound=TableRenderable)


def rich_renderable_as_table(cls: type[T]) -> type[T]:
    """Class decorator that adds a __rich__ method to a TableRenderable class."""
    setattr(cls, "__rich__", lambda x: to_table(cls, [x]))
    return cls
