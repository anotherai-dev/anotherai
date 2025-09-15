import os
from typing import Any, override

from structlog import get_logger
from taskiq import SimpleRetryMiddleware, TaskiqEvents, TaskiqMessage, TaskiqResult, TaskiqState

import core.logs.global_setup
from core.domain.exceptions import InternalError
from core.domain.metrics import send_counter, send_gauge
from protocol._common.broker_utils import use_in_memory_broker
from protocol._common.errors import configure_scope_for_error
from protocol._common.lifecycle import shutdown, startup

_log = get_logger(__name__)
_log.propagate = True


def _broker():
    broker_url = os.environ.get("JOBS_BROKER_URL")
    if use_in_memory_broker(broker_url):
        from taskiq import InMemoryBroker

        return InMemoryBroker()

    if not broker_url:
        raise ValueError("JOBS_BROKER_URL is not set")

    if broker_url.startswith("redis"):
        from taskiq_redis import ListQueueBroker

        return ListQueueBroker(url=broker_url)

    raise ValueError(f"Unknown broker URL: {broker_url}")


class ErrorMiddleware(SimpleRetryMiddleware):
    @override
    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ):
        is_fatal = isinstance(exception, InternalError) and exception.fatal
        msg = (
            f"Fatal error while executing task {message.task_name}"
            if is_fatal
            else f"Retriable Error while executing task {message.task_name}"
        )
        with configure_scope_for_error(
            exception,
            {"job": True, "transaction": message.task_name},
            extras={"args": message.args, "kwargs": message.kwargs},
        ):
            _log.exception(msg, exc_info=exception)

        if is_fatal:
            return

        send_counter("job_retry", task_name=message.task_name)
        await super().on_error(message, result, exception)

    @override
    async def post_execute(
        self,
        message: "TaskiqMessage",
        result: "TaskiqResult[Any]",
    ) -> None:
        """
        This function tracks number of errors and success executions.

        :param message: received message.
        :param result: result of the execution.
        """
        send_gauge(
            name="job_execution_time",
            value=result.execution_time,
            task_name=message.task_name,
            error=result.is_err,
        )


broker = _broker().with_middlewares(
    # TODO: add backoff and jitter
    ErrorMiddleware(default_retry_count=3),
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def worker_startup(state: TaskiqState):
    dependencies = await startup()
    state.dependencies = dependencies


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def worker_shutdown(state: TaskiqState):
    await shutdown(state.dependencies)
