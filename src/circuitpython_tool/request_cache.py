"""Cache of request URLs to payloads."""

from logging import getLogger
from pathlib import Path
from urllib.parse import quote

from .dirs import cache_dir

logger = getLogger(__name__)

CACHE_DIR = cache_dir / "requests"


class RequestCache:
    """Simple dict-like mapping of URLs to payloads backed by the filesystem.

    Each URL is mapped to a path on the filesystem. All operations go directly
    to the filesystem.
    """

    def __init__(self) -> None:
        logger.debug(f"Using {CACHE_DIR} as request cache directory.")

    def __getitem__(self, url: str) -> bytes:
        try:
            return self.path(url).read_bytes()
        except FileNotFoundError:
            raise KeyError(url)

    def __setitem__(self, url: str, data: bytes) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.path(url).write_bytes(data)

    def __contains__(self, url: str) -> bool:
        return self.path(url).exists()

    def path(self, url: str) -> Path:
        """Filesystem path for caching this URL's data.

        This just computes what the path should be; the path might not actually exist.
        """
        return CACHE_DIR / quote(url, safe="")
