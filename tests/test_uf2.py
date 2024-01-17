from dataclasses import asdict, dataclass, field
from json import dumps
from typing import Any

import pytest

from circuitpython_tool import uf2
from circuitpython_tool.uf2 import Board, Version


@dataclass
class FakeVersion:
    version: str
    stable: bool
    languages: list[str]
    # Most tests will be using the common case of a .uf2 extension.
    extensions: list[str] = field(default_factory=lambda: ["uf2"])


@dataclass
class FakeBoard:
    id: str
    downloads: int = 0
    versions: list[FakeVersion] = field(default_factory=list)

    def add_version(self, *args: Any, **kwargs: Any) -> "FakeBoard":
        self.versions.append(FakeVersion(*args, **kwargs))
        return self


class FakeBoardsJson:
    def __init__(self) -> None:
        self.boards: list[Any] = []

    def add_board(self, id: str, *args: Any, **kwargs: Any) -> FakeBoard:
        board = FakeBoard(id, *args, **kwargs)
        self.boards.append(board)
        return board

    def to_json(self) -> str:
        return dumps([asdict(b) for b in self.boards])


# Marked as autouse so that even if a test doesn't specify the fixture we don't
# accidentally spam real HTTP requests.
@pytest.fixture(autouse=True)
def fake_boards_json(monkeypatch: pytest.MonkeyPatch) -> FakeBoardsJson:
    """Fixture to bypass external HTTP requests and inject arbitrary JSON payloads."""
    fake_boards = FakeBoardsJson()
    monkeypatch.setattr(uf2, "cached_boards_json", fake_boards.to_json)
    return fake_boards


def test_empty_boards(fake_boards_json: FakeBoardsJson) -> None:
    assert Board.all() == []


def test_board_without_uf2_extension(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("my_board").add_version(
        "v1", stable=True, languages=["en_US"], extensions=["bin"]
    )

    assert Board.all() == []


def test_board_multiple_extensions(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("a").add_version(
        "v1", stable=True, languages=["en_US"], extensions=["bin", "uf2"]
    )

    assert Board.all() == [Board("a", stable_version=Version("v1", locales=["en_US"]))]


def test_board_only_stable_version(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("a").add_version("v1", stable=True, languages=["en_US"])

    assert Board.all() == [Board("a", stable_version=Version("v1", locales=["en_US"]))]


def test_board_only_unstable_version(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("a").add_version("v2", stable=False, languages=["en_US"])

    assert Board.all() == [
        Board("a", unstable_version=Version("v2", locales=["en_US"]))
    ]


def test_board_stable_and_unstable_version(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("a").add_version(
        "v1", stable=True, languages=["en_US"]
    ).add_version("v2", stable=False, languages=["en_US"])

    assert Board.all() == [
        Board(
            "a",
            stable_version=Version("v1", locales=["en_US"]),
            unstable_version=Version("v2", locales=["en_US"]),
        )
    ]


def test_board_download_count(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("a", downloads=123).add_version(
        "v1", stable=True, languages=["en_US"]
    )

    boards = Board.all()
    assert len(boards) == 1
    assert boards[0].download_count == 123


def test_multiple_boards(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("a").add_version("v1", stable=True, languages=["en_US"])
    fake_boards_json.add_board("b").add_version("v1", stable=True, languages=["en_US"])

    assert Board.all() == [
        Board("a", stable_version=Version("v1", locales=["en_US"])),
        Board("b", stable_version=Version("v1", locales=["en_US"])),
    ]


def test_all_languages(fake_boards_json: FakeBoardsJson) -> None:
    # One board with multiple English locales in a single version
    fake_boards_json.add_board("english").add_version(
        "v1", stable=True, languages=["en_US", "en_GB"]
    )
    # A pair of boards adding different Spanish locales
    fake_boards_json.add_board("spain").add_version(
        "v1", stable=True, languages=["es_ES"]
    )
    fake_boards_json.add_board("mexico").add_version(
        "v1", stable=True, languages=["es_MX"]
    )
    # One board with multiple versions adding different languages.
    fake_boards_json.add_board("belgium").add_version(
        "vfrench", stable=True, languages=["fr_BE"]
    ).add_version("vdutch", stable=False, languages=["nl_BE"])
    # A board with some overlap with other boards above, to check that
    # duplicates are filtered out.
    fake_boards_json.add_board("usa").add_version(
        "v1", stable=True, languages=["en_US", "es_MX"]
    )

    assert Board.all_locales() == [
        "en_GB",
        "en_US",
        "es_ES",
        "es_MX",
        "fr_BE",
        "nl_BE",
    ]


def test_download_url(fake_boards_json: FakeBoardsJson) -> None:
    fake_boards_json.add_board("raspberry_pi_pico").add_version(
        "8.2.9", stable=True, languages=["de_DE"]
    )

    boards = Board.all()
    assert len(boards) == 1
    board = boards[0]

    expected_url = (
        "https://adafruit-circuit-python.s3.amazonaws.com/bin/raspberry_pi_pico/de_DE/"
        "adafruit-circuitpython-raspberry_pi_pico-de_DE-8.2.9.uf2"
    )
    assert board.download_url(board.most_recent_version, "de_DE") == expected_url
