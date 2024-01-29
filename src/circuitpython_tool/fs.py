import logging
import re
import shutil
from asyncio import sleep
from collections.abc import AsyncIterator, Iterable, Iterator
from pathlib import Path

from inotify_simple import INotify as INotifySimple  # type: ignore
from inotify_simple import flags

from .async_iter import time_batched
from .inotify import INotify, Mask

logger = logging.getLogger(__name__)


def walk(root: Path) -> Iterator[Path]:
    """Recursively yields `root` and all descendant paths.

    This is a replacement for Path.walk, which is only available in Python
    3.12+.
    """
    yield root
    for path in root.iterdir():
        if path.is_dir():
            try:
                yield from walk(path)
            except PermissionError as e:
                logging.debug(f"Skipping {path}: {e}")
        else:
            yield path


def walk_all(roots: Iterable[Path]) -> Iterator[tuple[Path, Path]]:
    """Generator that yields tuples of (top-level source directory, descendant path)."""
    for root in roots:
        for path in walk(root):
            yield root, path


def guess_source_dir(start_dir: Path) -> Path | None:
    """Finds the directory containing the user's CircuitPython code, starting from `start_dir`.

    The search succeeds when we find a directory containing code.py, code.txt, main.py, or main.txt

    If no such file was found, None is returned.
    """
    for path in walk(start_dir):
        if not path.is_file():
            continue
        if re.fullmatch(r"(code|main)\.(py|txt)", path.name):
            return path.parent
    return None


def watch_all(roots: Iterable[Path]) -> Iterator[set[Path]]:
    watcher = INotifySimple()

    # Maps inotify descriptors to roots.
    descriptor_to_root = {}
    for _, path in walk_all(roots):
        if not path.is_dir():
            continue
        logger.debug(f"Watching directory {path} for changes.")
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


def watch_all2(roots: Iterable[Path], read_delay: float) -> AsyncIterator[set[Path]]:
    """Watches a set of directories for changes in any descendant paths."""
    watcher = INotify()
    for _, path in walk_all(roots):
        if not path.is_dir():
            continue
        logger.info(f"Watching directory {path} for changes.")
        watcher.add_watch(
            path,
            Mask.CREATE | Mask.MODIFY | Mask.ATTRIB | Mask.DELETE | Mask.DELETE_SELF,
        )

    async def gen() -> AsyncIterator[set[Path]]:
        async for event_batch in time_batched(
            watcher.events(), delay=lambda: sleep(read_delay)
        ):
            logging.debug(f"Filesystem event_batch: {event_batch}")
            modified_paths = set()
            for event in event_batch:
                # Don't need to explicitly remove watches; DELETE* events will
                # automatically do that.
                #
                # TODO(dhrosa): Automatically watch new child directories
                modified_paths.add(event.path)
            yield modified_paths

    return gen()


def upload(source_dirs: Iterable[Path], mountpoint: Path) -> None:
    """Copy all source files onto the device."""
    for source_dir, source in walk_all(source_dirs):
        if source.name[0] == "." or source.is_dir():
            continue
        rel_path = source.relative_to(source_dir)
        dest = mountpoint / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            # Round source timestamp to 2s resolution to match FAT drive.
            # This prevents spurious timestamp mismatches.
            source_mtime = (source.stat().st_mtime // 2) * 2
            dest_mtime = dest.stat().st_mtime
            if source_mtime == dest_mtime:
                continue
        logger.info(f"Copying {source_dir / rel_path}")
        shutil.copy2(source, dest)
    logger.info("Upload complete")
