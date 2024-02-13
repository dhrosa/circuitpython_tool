"""Functions for interacting with UF2 files."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from json import loads
from urllib.request import urlopen

from .iter import as_list
from .request_cache import RequestCache

logger = logging.getLogger(__name__)

BASE_URL = "https://circuitpython.org"


def cached_boards_json() -> str:
    """JSON blob of CircuitPython-supposed boards.

    The data is fetched from circuitpython.org's github repo and cached to disk.
    """
    url = "https://raw.githubusercontent.com/adafruit/circuitpython-org/main/_data/files.json"
    cache = RequestCache()
    if url in cache:
        logging.debug("Using cached data for CircuitPython boards JSON.")
        return str(cache[url], encoding="utf-8")
    logging.debug(
        f"CircuitPython boards JSON not found in cached; populating from {url}"
    )
    with urlopen(url) as request:
        data = request.read()
    cache[url] = data
    return str(data, encoding="utf-8")


@dataclass
class Version:
    """A CircuitPython release for a board."""

    label: str
    """Version string."""

    locales: list[str]
    """Supported locales for this release"""


@dataclass
class Board:
    id: str
    # Note: at least one of these two fields will always be set for instances
    # returned by Board.all()
    stable_version: Version | None = None
    unstable_version: Version | None = None

    download_count: int = 0

    @property
    @as_list
    def versions(self) -> Iterator[Version]:
        """List of available versions, sorted from most to least stable."""
        if self.stable_version:
            yield self.stable_version
        if self.unstable_version:
            yield self.unstable_version

    @property
    def most_stable_version(self) -> Version:
        return self.versions[0]

    @property
    def most_recent_version(self) -> Version:
        return self.versions[-1]

    @as_list
    @staticmethod
    def all() -> Iterator["Board"]:
        """All available boards, sorted by decreasing popularity."""
        for board_json in loads(cached_boards_json()):
            board = Board(board_json["id"])
            for version_json in board_json["versions"]:
                if "uf2" not in version_json["extensions"]:
                    continue
                version = Version(
                    label=version_json["version"], locales=version_json["languages"]
                )
                # Note: this depends on there being at most one stable and one
                # unstable version.
                if version_json["stable"]:
                    board.stable_version = version
                else:
                    board.unstable_version = version
            if not (board.stable_version or board.unstable_version):
                continue
            board.download_count = board_json["downloads"]
            yield board

    @staticmethod
    def by_id(board_id: str) -> "Board":
        """Lookup a Board by ID."""
        boards = {b.id: b for b in Board.all()}
        return boards[board_id]

    @staticmethod
    def all_locales() -> list[str]:
        """Set of all potentially valid locale codes, sorted alphabetically."""
        locales: set[str] = set()
        for b in Board.all():
            for v in b.versions:
                locales |= set(v.locales)
        return sorted(locales)

    def download_url(self, version: Version, locale: str) -> str:
        """URL for downloading CircuitPython UF2 image."""
        # Derived from
        # https://github.com/adafruit/circuitpython-org/blob/c98c065889eef027447ff2b2e46cd4f15806e522/tools/generate-board-info.py#L42C1-L43C1
        prefix = "https://adafruit-circuit-python.s3.amazonaws.com/bin"
        dir = f"{self.id}/{locale}"
        file = f"adafruit-circuitpython-{self.id}-{locale}-{version.label}.uf2"
        return f"{prefix}/{dir}/{file}"
