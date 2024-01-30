"""Async iterator utilities."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from typing import TypeVar

T = TypeVar("T")


async def time_batched(
    source: AsyncIterator[T], delay: Callable[[], Awaitable[None]]
) -> AsyncIterator[list[T]]:
    """Asynchronous iterator that batches together input elements.

    Each batch contains at least one element. Once the first element of the
    batch is fetched from the input, we await the result of `delay()`, and all
    input items that are fetched while waiting are included in the batch.

    e.g. using delay=lambda: asyncio.sleep(1) will group together all items that
    arrive within 1 second of the first item in the batch.
    """

    # Using a queue for incoming elements lets us fetch all available elements
    # without blocking.
    queue: asyncio.Queue[T] = asyncio.Queue()

    async def save_to_queue() -> None:
        async for x in source:
            queue.put_nowait(x)

    async def next_batch() -> list[T]:
        # Unconditionally wait for first item in batch.
        batch = [await queue.get()]
        # Wait for other items to build up in queue.
        await delay()
        # Drain the queue of any pending items.
        with suppress(asyncio.QueueEmpty):
            while True:
                batch.append(queue.get_nowait())
        return batch

    # Collect input into queue in the background.
    queue_task = asyncio.create_task(save_to_queue())

    try:
        while True:
            yield await next_batch()
    finally:
        # Clean up background task before exit.
        queue_task.cancel()
        with suppress(asyncio.CancelledError):
            await queue_task
