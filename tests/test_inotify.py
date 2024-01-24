import asyncio
from pathlib import Path

from circuitpython_tool.inotify import INotify, flags


def test_lol(tmp_path: Path) -> None:
    watcher = INotify()

    assert watcher.fd > 2
    watcher.add_watch(tmp_path, flags.CREATE | flags.MODIFY)

    async def body() -> None:
        events = watcher.events()
        (tmp_path / "create.txt").touch()
        async with asyncio.timeout(2):
            assert (await anext(events)).path.relative_to(tmp_path) == Path(
                "create.txt"
            )

    asyncio.run(body(), debug=True)
