"""High-level filesystem operations."""

import logging
import re
import shutil
from collections.abc import AsyncIterator, Iterable, Iterator
from pathlib import Path

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


def watch_all(roots: Iterable[Path]) -> AsyncIterator[Path]:
    """Watches a set of directories for changes in any descendant paths.

    Each time a path is modified, that path is yielded. Any newly created
    descendant directories are automatically watched.

    """

    # Note: We eagerly create the watcher first and then create the coroutine. If we
    # created the watcher directly within the coroutine, then the inotify code
    # would not start up until the first element of the coroutine was requested.
    #
    # By eagerly creating the watcher instead, this lets us respond to events
    # that happen between the call to this function and iterating over the first
    # element of the coroutine.
    watcher = INotify()
    mask = Mask.CREATE | Mask.MODIFY | Mask.ATTRIB | Mask.DELETE | Mask.DELETE_SELF
    for _, path in walk_all(roots):
        if not path.is_dir():
            continue
        logger.info(f"Watching directory {path} for changes.")
        watcher.add_watch(path, mask)

    async def gen() -> AsyncIterator[Path]:
        async for event in watcher.events():
            logging.debug(f"Filesystem event: {event}")
            if Mask.CREATE in event.mask and event.path.is_dir():
                logger.info(f"Watching newly created directory {path} for changes.")
                watcher.add_watch(event.path, mask)
            # Note: We don't need to specially handle DELETE events on
            # directories; deleted directories are automatically removed from
            # the watch via the IN_IGNORED mask:
            # https://man7.org/linux/man-pages/man7/inotify.7.html#:~:text=read(2)%3A-,IN_IGNORED,-Watch%20was%20removed
            yield event.path

    return gen()


def upload(source_dirs: Iterable[Path], mountpoint: Path) -> None:
    """Copy all source files onto the device."""
    # TODO(dhrosa): shutil.copytree() with a custom `copy_function` or `ignore`
    # argument would probably be simpler.
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
