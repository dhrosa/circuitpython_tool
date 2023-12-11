import logging
from pathlib import Path

from inotify_simple import INotify, flags

logger = logging.getLogger(__name__)


def walk_all(roots: list[Path]):
    """Generator that yields tuples of (top-level source directory, descendant path)."""
    for root in roots:
        yield root, root
        # Path.walk requires Python 3.12 or higher, so we roll our own here.
        for path in root.iterdir():
            if path.is_dir():
                yield from walk_all([path])
            else:
                yield root, path


def watch_all(roots: list[Path]):
    watcher = INotify()

    # Maps inotify descriptors to roots.
    descriptor_to_root = {}
    for _, path in walk_all(roots):
        if not path.is_dir():
            continue
        logger.info(f"Watching directory {str(path)} changes.")
        descriptor = watcher.add_watch(
            path,
            flags.CREATE
            | flags.MODIFY
            | flags.ATTRIB
            | flags.DELETE
            | flags.DELETE_SELF,
        )
        descriptor_to_root[descriptor] = path

    while True:
        modified_paths = set()
        # Use a small read_delay to coalesce short bursts of events (e.g.
        # copying multiple files from another location).
        for event in watcher.read(read_delay=100):
            root = descriptor_to_root[event.wd]
            modified_paths.add(root / event.name)
        if modified_paths:
            yield modified_paths
