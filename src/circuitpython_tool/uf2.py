import logging
from dataclasses import dataclass
from json import loads

import requests

from .dirs import app_dir

logger = logging.getLogger(__name__)

BASE_URL = "https://circuitpython.org"


def cached_boards_json() -> str:
    # TODO(dhrosa): Re-download when the file is stale.
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
    # Note: at least one of these will always be set.
    stable_version: Version | None = None
    unstable_version: Version | None = None

    @property
    def versions(self) -> list[Version]:
        """List of available versions, sorted from most to least stable."""
        versions: list[Version] = []
        if self.stable_version:
            versions.append(self.stable_version)
        if self.unstable_version:
            versions.append(self.unstable_version)
        return versions

    @property
    def most_stable_version(self) -> Version:
        return self.versions[0]

    @property
    def most_recent_version(self) -> Version:
        return self.versions[-1]

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
                # Note: this depends on there being at most one stable and one
                # unstable version.
                if version_json["stable"]:
                    board.stable_version = version
                else:
                    board.unstable_version = version
            if not (board.stable_version or board.unstable_version):
                continue
            boards[board.id] = board
        return boards

    def download_url(self, version: Version, language: str) -> str:
        # Derived from
        # https://github.com/adafruit/circuitpython-org/blob/c98c065889eef027447ff2b2e46cd4f15806e522/tools/generate-board-info.py#L42C1-L43C1
        prefix = "https://adafruit-circuit-python.s3.amazonaws.com/bin"
        dir = f"{self.id}/{language}"
        file = f"adafruit-circuitpython-{self.id}-{language}-{version.label}.uf2"
        return f"{prefix}/{dir}/{file}"
