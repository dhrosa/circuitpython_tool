"""Library for rendering objects with Rich."""

from collections.abc import Iterable, Iterator
from typing import Any, Protocol, TypeAlias, TypeVar, cast

from rich.console import RenderableType
from rich.protocol import is_renderable
from rich.table import Table

TableField: TypeAlias = tuple[str, str] | str


class TableRenderable(Protocol):
    """Protocol for pretty printing objects using Rich tables."""

    @classmethod
    def __table_fields__(cls) -> Iterator[TableField]:
        """Each property to be identified by its attribute name.

        The value to render in the table is lookuped up from each item instance
        by the attribute name. If the attribute name specifies a method, the
        method is automatically called to fetch the value to render.

        If a field is just a single string, then the column name is the same as
        the attribute name.

        If a field is a pair of strings, the first element of the pair is used
        as the column name, and the second element is the attribute name.

        """
        ...


T = TypeVar("T", bound=TableRenderable)


def to_table(element_type: type[TableRenderable], items: Iterable[T]) -> Table:
    """Render `items` into a table, with each row corresponding to one item.

    Each item must be of type `element_type`.
    """

    # Mapping of labels to attribute names.
    fields = dict[str, str]()
    for f in element_type.__table_fields__():
        if isinstance(f, str):
            f = (f, f)
        fields[f[0]] = f[1]

    table = Table()
    for key in fields.keys():
        table.add_column(key)

    for item in items:
        row = list[Any]()
        # Map attribute names to values
        for attribute_name in fields.values():
            row.append(get_field_value(item, attribute_name))
        table.add_row(*row)

    return table


def get_field_value(item: Any, attribute_name: str) -> RenderableType:
    value: Any = getattr(item, attribute_name)
    if callable(value):
        value = value()
    if is_renderable(value):
        return cast(RenderableType, value)
    return str(value)
