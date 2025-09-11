import asyncio
from collections.abc import Sequence
from typing import Generic, NamedTuple, TypeVar

from structlog import get_logger

from core.domain.events import Event, StoreCompletionEvent, UserConnectedEvent
from protocol.worker.tasks._types import TASK

_log = get_logger(__name__)

# Using old generic syntax to force the type to be covariant
_T_co = TypeVar("_T_co", bound=Event, covariant=True)


class _TaskListing(NamedTuple, Generic[_T_co]):  # noqa: UP046
    event: type[_T_co]
    jobs: Sequence[TASK[_T_co]]


def _tasks() -> Sequence[_TaskListing[Event]]:
    # Importing here to avoid circular dependency
    from protocol.worker.tasks import store_completion_tasks, user_connected_tasks

    # We use an array to have correct typing
    return [
        _TaskListing(StoreCompletionEvent, store_completion_tasks.TASKS),
        _TaskListing(UserConnectedEvent, user_connected_tasks.TASKS),
    ]


class SystemEventRouter:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()
        self._handlers: dict[type[Event], _TaskListing[Event]] = {job.event: job for job in _tasks()}

    @classmethod
    async def _send_task[T: Event](
        cls,
        job: TASK[T],
        event: T,
        delay: float | None = None,
    ):
        try:
            if delay:
                await asyncio.sleep(delay)

            await job.kiq(event)
        except Exception as e:  # noqa: BLE001
            # We retry once, see https://github.com/redis/redis-py/issues/2491
            # We added the hiredis parser so this should not happen
            _log.warning("Error sending job, retrying", exc_info=e)
            try:
                await job.kiq(event)
            except Exception:  # noqa: BLE001
                _log.exception("Error sending job")

    def _schedule_task(
        self,
        job: TASK[Event],
        event: Event,
        delay: float | None = None,
    ):
        t = asyncio.create_task(self._send_task(job, event, delay=delay))
        self._tasks.add(t)
        t.add_done_callback(self._tasks.remove)

    def __call__(self, event: Event, delay: float | None = None) -> None:
        try:
            listing = self._handlers[type(event)]

            for job in listing.jobs:
                self._schedule_task(job, event, delay)

        except KeyError as e:
            _log.exception("Missing event handler", exc_info=e)
            return
        except Exception as e:  # noqa: BLE001
            # This one should never happen
            _log.exception("Error handling event", exc_info=e)


class TenantEventRouter:
    def __init__(
        self,
        tenant_uid: int,
        system_event_router: SystemEventRouter,
    ) -> None:
        self.tenant_uid = tenant_uid
        self.system_event_router = system_event_router

    def __call__(self, event: Event, delay: float | None = None) -> None:
        event.tenant_uid = self.tenant_uid
        self.system_event_router(event, delay)
