"""Async wrapper around Linux inotify API.

https://man7.org/linux/man-pages/man7/inotify.7.html for full inotify
documentation.

Inspired by https://github.com/chrisjbillington/inotify_simple and
https://github.com/chrisjbillington/inotify_simple

"""

import asyncio
import os
import struct
from asyncio import Queue
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from ctypes import CDLL, get_errno
from ctypes.util import find_library
from dataclasses import dataclass
from enum import Flag
from errno import EINTR
from functools import wraps
from pathlib import Path
from typing import ParamSpec


class Mask(Flag):
    """Inotify flags as defined in ``inotify.h`` but with ``IN_`` prefix omitted."""

    ACCESS = 0x00000001  # File was accessed
    MODIFY = 0x00000002  # File was modified
    ATTRIB = 0x00000004  # Metadata changed
    CLOSE_WRITE = 0x00000008  # Writable file was closed
    CLOSE_NOWRITE = 0x00000010  # Unwritable file closed
    OPEN = 0x00000020  # File was opened
    MOVED_FROM = 0x00000040  # File was moved from X
    MOVED_TO = 0x00000080  # File was moved to Y
    CREATE = 0x00000100  # Subfile was created
    DELETE = 0x00000200  # Subfile was deleted
    DELETE_SELF = 0x00000400  # Self was deleted
    MOVE_SELF = 0x00000800  # Self was moved

    UNMOUNT = 0x00002000  # Backing fs was unmounted
    Q_OVERFLOW = 0x00004000  # Event queue overflowed
    IGNORED = 0x00008000  # File was ignored

    ONLYDIR = 0x01000000  # only watch the path if it is a directory
    DONT_FOLLOW = 0x02000000  # don't follow a sym link
    EXCL_UNLINK = 0x04000000  # exclude events on unlinked objects
    MASK_ADD = 0x20000000  # add to the mask of an already existing watch
    ISDIR = 0x40000000  # event occurred against dir
    ONESHOT = 0x80000000  # only send event once


P = ParamSpec("P")


def retry_on_eintr(f: Callable[P, int]) -> Callable[P, int]:
    """Decorator to retry libc-style function on EINTR."""

    @wraps(f)
    def inner(*args: P.args, **kwargs: P.kwargs) -> int:
        while True:
            if (result := f(*args, **kwargs)) != -1:
                return result
            if (errno := get_errno()) != EINTR:
                raise OSError(errno, os.strerror(errno))

    return inner


libc = CDLL(find_library("c") or "libc.so.6", use_errno=True)
inotify_init1 = retry_on_eintr(libc.inotify_init1)
inotify_add_watch = retry_on_eintr(libc.inotify_add_watch)


@dataclass
class Event:
    """Corresponds roughly to the inotify_event struct."""

    mask: Mask
    """Bit mask detailing what triggered this event."""

    path: Path
    """Path the event relates to (e.g. the file name of a newly created file)."""


@contextmanager
def async_read_fd(fd: int, read_callback: Callable[[], None]) -> Iterator[None]:
    """Context manager for monitoring a file descriptor for read events with asyncio.

    Must be called within an async context. Unregisters the file descriptor when
    the context manager exits.
    """

    # TODO(dhrosa): Get rid of callback and return an AsyncIterator
    loop = asyncio.get_running_loop()
    loop.add_reader(fd, read_callback)
    try:
        yield
    finally:
        loop.remove_reader(fd)


class INotify:
    """Wrapper around an inotify instance."""

    def __init__(self) -> None:
        # Don't transfer file descriptor to subprocesses, and set it up for
        # non-blocking reads.
        self.fd = inotify_init1(os.O_CLOEXEC | os.O_NONBLOCK)
        # Maps watch descriptor values to their Path
        self.watch_descriptor_to_path: dict[int, Path] = {}

    def add_watch(self, path: Path, mask: Mask) -> None:
        """Adds a new path to the inotify watch set."""
        descriptor = inotify_add_watch(self.fd, os.fsencode(path), mask.value)
        self.watch_descriptor_to_path[descriptor] = path

    async def events(self) -> AsyncIterator[Event]:
        """Asynchronous generator for inotify events."""
        queue: Queue[bytes] = Queue()
        with os.fdopen(self.fd, "rb") as f, async_read_fd(
            self.fd, lambda: queue.put_nowait(f.read())
        ):
            while True:
                for event in self.parse_events(await queue.get()):
                    yield event

    def parse_events(self, data: bytes) -> Iterator[Event]:
        """Parse data from inotify file descriptor into a series of Event objects.

        We assume `data` does not contain any partial event structs.
        """
        EVENT_FORMAT = "iIII"
        EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
        pos = 0
        while pos < len(data):
            watch_descriptor, mask, cookie, name_length = struct.unpack_from(
                EVENT_FORMAT, data, pos
            )
            pos += EVENT_SIZE
            raw_name = data[pos : (pos + name_length)]
            pos += name_length
            # Name is null-terminated if non-empty, but may contain arbitrary extra
            # null bytes at the end.
            name_bytes = raw_name[: raw_name.find(0)]
            # Event path is relative to the path corresponding to the watch descriptor
            base_path = self.watch_descriptor_to_path[watch_descriptor]
            yield Event(mask=Mask(mask), path=base_path / os.fsdecode(name_bytes))
