import time
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from typing import Any, ClassVar

from pydantic import BaseModel, Field
from structlog import get_logger

from core.utils.background import add_background_task


async def _noop_sender(metric: "Metric", *args: Any, **kwargs: Any):
    get_logger(__name__).debug("Noop sender for metric", metric=metric)


# TODO: switch to using log


class Metric(BaseModel):
    name: str
    timestamp: float = Field(default_factory=time.time)
    tags: dict[str, int | str | float | bool] = Field(default_factory=dict)

    gauge: float | None = None
    counter: int | None = None

    sender: ClassVar[Callable[["Metric"], Awaitable[None]]] = _noop_sender

    async def send(self):
        await self.__class__.sender(self)

    @classmethod
    def reset_sender(cls):
        cls.sender = _noop_sender


def send_counter(name: str, value: int = 1, **tags: str | float | bool | None):
    # No need to catch exceptions here, add_background_task wraps coroutines in try/catch
    add_background_task(Metric(name=name, counter=value, tags={k: v for k, v in tags.items() if v is not None}).send())


# TODO: switch to sync like send_counter
async def send_gauge(name: str, value: float, timestamp: float | None = None, **tags: str | float | bool | None):
    try:
        await Metric(
            name=name,
            gauge=value,
            timestamp=timestamp or time.time(),
            tags={k: v for k, v in tags.items() if v is not None},
        ).send()
    except Exception:  # noqa: BLE001
        get_logger(__name__).exception("Failed to send gauge metric", name=name, tags=tags)


@contextmanager
def measure_time(name: str, **tags: str | float | bool | None):
    start = time.time()
    try:
        yield
    finally:
        add_background_task(
            send_gauge(name, time.time() - start, timestamp=start, **tags),
        )
