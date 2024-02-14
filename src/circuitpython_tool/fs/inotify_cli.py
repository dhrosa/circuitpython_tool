import asyncio
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import cast

import rich_click as click
from rich import print

from .inotify import INotify, Mask


@click.command
@click.argument(
    "path",
    required=True,
    type=click.Path(path_type=Path, exists=True),
)
@click.argument(
    "mask_strings",
    type=click.Choice([cast(str, m.name) for m in Mask], case_sensitive=False),
    required=True,
    nargs=-1,
)
def main(path: Path, mask_strings: list[str]) -> None:
    """Simple utility for manually testing inotify events.

    Waits for inotify events and prints them as they arrive.
    """
    mask = reduce(Mask.__or__, (Mask[s] for s in mask_strings))
    print(f"Selected mask: {mask}")
    watcher = INotify()
    watcher.add_watch(path, mask)

    async def amain() -> None:
        async for event in watcher.events():
            print(f"[{datetime.now():%X}] {event.path.resolve()} : {event.mask}")

    asyncio.run(amain())


if __name__ == "__main__":
    main()
