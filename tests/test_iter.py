from collections.abc import Iterator

from circuitpython_tool.iter import as_list


def test_as_list_function() -> None:
    @as_list
    def f(a: int, b: int) -> Iterator[int]:
        yield a
        yield b

    assert f(1, 2) == [1, 2]


def test_as_list_method() -> None:
    class C:
        @as_list
        def f(self, a: int, b: int) -> Iterator[int]:
            yield a
            yield b

    assert C().f(1, 2) == [1, 2]
