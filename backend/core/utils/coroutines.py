from collections.abc import Coroutine
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, override

from sentry_sdk import capture_exception
from structlog.typing import FilteringBoundLogger


def sentry_wrap[T](
    corot: Coroutine[Any, Any, T],
    logger: FilteringBoundLogger | None = None,
) -> Coroutine[Any, Any, T | None]:
    async def captured() -> T | None:
        try:
            return await corot
        except Exception as e:
            if logger:
                logger.exception("Error in background task", exc_info=e)
            else:
                capture_exception(e)
            return None

    return captured()


class capture_errors(AbstractContextManager[None]):  # noqa: N801
    def __init__(self, logger: FilteringBoundLogger, msg: str):
        super().__init__()
        self._logger = logger
        self._msg = msg

    def __enter__(self):
        pass

    # Returning a bool here makes pyright understand that the context manager can suppress exceptions
    @override
    def __exit__(
        self,
        exctype: type[BaseException] | None,
        excinst: BaseException | None,
        exctb: TracebackType | None,
    ) -> bool:
        if exctype is None:
            return False

        self._logger.exception(self._msg, exc_info=excinst)
        return True
