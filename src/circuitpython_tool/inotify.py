import asyncio
import os
import struct
from asyncio import Queue
from collections.abc import AsyncIterator, Callable, Iterator
from ctypes import CDLL, get_errno
from ctypes.util import find_library
from dataclasses import dataclass
from enum import IntEnum
from errno import EINTR
from functools import wraps
from pathlib import Path
from typing import ParamSpec

P = ParamSpec("P")


def retry_on_eintr(f: Callable[P, int]) -> Callable[P, int]:
    """Wrapper to retry libc-style function on EINTR."""

    @wraps(f)
    def inner(*args: P.args, **kwargs: P.kwargs) -> int:
        while True:
            result = f(*args, **kwargs)
            if result != -1:
                return result
            errno = get_errno()
            if errno != EINTR:
                raise OSError(errno, os.strerror(errno))

    return inner


libc = CDLL(find_library("c") or "libc.so.6", use_errno=True)

inotify_init1 = retry_on_eintr(libc.inotify_init1)
inotify_add_watch = retry_on_eintr(libc.inotify_add_watch)


@dataclass
class Event:
    """Corresponds to inotify_event struct."""

    # watch_descriptor: int
    # mask: int
    # cookie: int
    path: Path


class INotify:
    def __init__(self) -> None:
        self.fd = inotify_init1(os.O_NONBLOCK)
        self.f = os.fdopen(self.fd, "rb")
        self.watch_descriptor_to_path: dict[int, Path] = {}

    def add_watch(self, path: Path, mask: int) -> None:
        descriptor = inotify_add_watch(self.fd, os.fsencode(path), mask)
        self.watch_descriptor_to_path[descriptor] = path

    async def events(self) -> AsyncIterator[Event]:
        queue: Queue[bytes] = Queue()

        loop = asyncio.get_event_loop()
        loop.add_reader(self.fd, lambda: queue.put_nowait(self.f.read()))
        try:
            while True:
                for event in self.parse_events(await queue.get()):
                    yield event
        finally:
            loop.remove_reader(self.fd)

    def parse_events(self, data: bytes) -> Iterator[Event]:
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
            name_bytes = raw_name[: raw_name.index(0)]
            path = self.watch_descriptor_to_path[watch_descriptor] / os.fsdecode(
                name_bytes
            )
            yield Event(path)


class flags(IntEnum):
    """Inotify flags as defined in ``inotify.h`` but with ``IN_`` prefix omitted.
    Includes a convenience method :func:`~inotify_simple.flags.from_mask` for extracting
    flags from a mask."""

    ACCESS = 0x00000001  #: File was accessed
    MODIFY = 0x00000002  #: File was modified
    ATTRIB = 0x00000004  #: Metadata changed
    CLOSE_WRITE = 0x00000008  #: Writable file was closed
    CLOSE_NOWRITE = 0x00000010  #: Unwritable file closed
    OPEN = 0x00000020  #: File was opened
    MOVED_FROM = 0x00000040  #: File was moved from X
    MOVED_TO = 0x00000080  #: File was moved to Y
    CREATE = 0x00000100  #: Subfile was created
    DELETE = 0x00000200  #: Subfile was deleted
    DELETE_SELF = 0x00000400  #: Self was deleted
    MOVE_SELF = 0x00000800  #: Self was moved

    UNMOUNT = 0x00002000  #: Backing fs was unmounted
    Q_OVERFLOW = 0x00004000  #: Event queue overflowed
    IGNORED = 0x00008000  #: File was ignored

    ONLYDIR = 0x01000000  #: only watch the path if it is a directory
    DONT_FOLLOW = 0x02000000  #: don't follow a sym link
    EXCL_UNLINK = 0x04000000  #: exclude events on unlinked objects
    MASK_ADD = 0x20000000  #: add to the mask of an already existing watch
    ISDIR = 0x40000000  #: event occurred against dir
    ONESHOT = 0x80000000  #: only send event once
