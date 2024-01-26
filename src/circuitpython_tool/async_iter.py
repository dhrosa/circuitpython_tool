import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import TypeVar

T = TypeVar("T")

default_sleep = asyncio.sleep


async def time_batched(
    source: AsyncIterator[T],
    batch_period: float,
    sleep: Callable[[float], Coroutine[None, None, None]] = default_sleep,
) -> AsyncIterator[list[T]]:
    async def fetch() -> T:
        return await anext(source)

    fetch_task = asyncio.create_task(fetch())

    async def next_batch() -> list[T]:
        nonlocal fetch_task
        batch = [await fetch_task]
        sleep_task = asyncio.create_task(sleep(batch_period))
        fetch_task = asyncio.create_task(fetch())
        while True:
            done, pending = await asyncio.wait(
                (sleep_task, fetch_task), return_when=asyncio.FIRST_COMPLETED
            )
            if fetch_task in done:
                batch.append(fetch_task.result())
                fetch_task = asyncio.create_task(fetch())
            elif sleep_task in done:
                return batch

    while True:
        yield await next_batch()
