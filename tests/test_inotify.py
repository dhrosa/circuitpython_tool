import asyncio
from pathlib import Path

from circuitpython_tool.inotify import INotify, Mask


def test_file_changes(tmp_path: Path) -> None:
    async def body() -> None:
        (tmp_path / "existing.txt").touch()

        watcher = INotify()
        watcher.add_watch(tmp_path, Mask.CREATE | Mask.MODIFY)

        events = watcher.events()
        (tmp_path / "created.txt").touch()
        event = await anext(events)
        assert event.path.relative_to(tmp_path) == Path("created.txt")
        assert Mask.CREATE in event.mask
        assert Mask.MODIFY not in event.mask

        (tmp_path / "existing.txt").write_text("new contents")
        event = await anext(events)
        assert event.path.relative_to(tmp_path) == Path("existing.txt")
        assert Mask.CREATE not in event.mask
        assert Mask.MODIFY in event.mask

    asyncio.run(asyncio.wait_for(body(), timeout=1), debug=True)
