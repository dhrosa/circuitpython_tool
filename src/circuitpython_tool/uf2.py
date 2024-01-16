import logging
from dataclasses import dataclass
from json import loads

import requests

from .dirs import app_dir

logger = logging.getLogger(__name__)

BASE_URL = "https://circuitpython.org"


def cached_boards_json() -> str:
    path = app_dir / "cached_boards.json"
    if path.exists():
        return path.read_text()
    url = "https://raw.githubusercontent.com/adafruit/circuitpython-org/main/_data/files.json"
    logger.info(f"Cached boards path {path} does not exist yet; populating from {url}")
    json = requests.get(url).text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json)
    return json


@dataclass
class Version:
    label: str
    languages: list[str]


@dataclass
class Board:
    id: str
    stable_version: Version | None = None
    unstable_version: Version | None = None

    @staticmethod
    def all() -> dict[str, "Board"]:
        json = loads(cached_boards_json())
        boards = {}
        for board_json in json:
            board = Board(board_json["id"])
            for version_json in board_json["versions"]:
                if "uf2" not in version_json["extensions"]:
                    continue
                version = Version(
                    label=version_json["version"], languages=version_json["languages"]
                )
                if version_json["stable"]:
                    board.stable_version = version
                else:
                    board.unstable_version = version
            if not (board.stable_version or board.unstable_version):
                continue
            boards[board.id] = board
        return boards
