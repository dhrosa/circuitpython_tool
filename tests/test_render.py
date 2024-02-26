from dataclasses import dataclass

from rich.table import Table

from circuitpython_tool.render import TableFields, to_table, to_table_single


@dataclass
class Number:
    value: int

    def square(self) -> int:
        return self.value**2

    @classmethod
    def __table_fields__(cls) -> TableFields:
        yield "value", lambda x: x.value
        yield "square", Number.square


def get_cells(table: Table) -> dict[str, list[str]]:
    """Convert a table to a mapping of (column name -> column values)."""
    cells = dict[str, list[str]]()
    for column in table.columns:
        cells[str(column.header)] = [str(v) for v in column.cells]
    return cells


def test_to_table() -> None:
    assert get_cells(to_table(Number, [Number(1), Number(2)])) == {
        "value": ["1", "2"],
        "square": ["1", "4"],
    }


def test_to_table_single() -> None:
    assert get_cells(to_table_single(Number(2))) == {
        "Property": ["value", "square"],
        "Value": ["2", "4"],
    }
