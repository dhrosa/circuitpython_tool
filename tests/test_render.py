from collections.abc import Iterator
from dataclasses import dataclass

from rich.table import Table

from circuitpython_tool.render import TableField, to_table


@dataclass
class Number:
    value: int

    def square(self) -> int:
        return self.value**2

    @classmethod
    def __table_fields__(cls) -> Iterator[TableField]:
        yield "value"
        yield "Labelled Value", "value"
        yield "square"
        yield "Labelled Square", "square"


def get_cells(table: Table) -> dict[str, list[str]]:
    """Convert a table to a mapping of (column name -> column values)."""
    cells = dict[str, list[str]]()
    for column in table.columns:
        cells[str(column.header)] = [str(v) for v in column.cells]
    return cells


def test_to_table() -> None:
    table = to_table(Number, [Number(1), Number(2)])
    assert get_cells(table) == {
        "value": ["1", "2"],
        "Labelled Value": ["1", "2"],
        "square": ["1", "4"],
        "Labelled Square": ["1", "4"],
    }
