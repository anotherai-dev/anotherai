import asyncio
from collections.abc import Coroutine
from typing import Any

from core.utils.coroutines import sentry_wrap


# TODO: this is super basic, only use for really small tasks
class BackgroundTasks:
    def __init__(self):
        self._tasks = set[asyncio.Task[None]]()

    def add(self, task: Coroutine[Any, Any, None]):
        t = asyncio.create_task(sentry_wrap(task))
        self._tasks.add(t)
        t.add_done_callback(self._tasks.remove)

    async def wait(self):
        if not self._tasks:
            return
        await asyncio.gather(*self._tasks)


_shared_background_tasks = BackgroundTasks()


def add_background_task(task: Coroutine[Any, Any, None]):
    _shared_background_tasks.add(task)


async def wait_for_background_tasks():
    await _shared_background_tasks.wait()
