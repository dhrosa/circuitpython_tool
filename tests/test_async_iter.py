import asyncio
from collections.abc import AsyncIterator

from circuitpython_tool.async_iter import time_batched


def test_batching() -> None:
    input_queue: asyncio.Queue[int] = asyncio.Queue()

    # Expose input_queue as an async generator
    async def gen() -> AsyncIterator[int]:
        while True:
            yield await input_queue.get()

    wake_event = asyncio.Event()

    # 'Delay' callback that is manually resumed by the caller.
    async def fake_sleep() -> None:
        await wake_event.wait()
        wake_event.clear()

    async def body() -> None:
        batched = time_batched(gen(), delay=fake_sleep)

        async def next_batch() -> list[int]:
            return await asyncio.wait_for(anext(batched), timeout=1)

        input_queue.put_nowait(0)
        wake_event.set()
        assert await next_batch() == [0]

        input_queue.put_nowait(1)
        input_queue.put_nowait(2)
        wake_event.set()
        assert await next_batch() == [1, 2]

    asyncio.run(body(), debug=True)
