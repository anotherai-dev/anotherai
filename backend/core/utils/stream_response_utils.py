from collections.abc import AsyncGenerator, AsyncIterator, Callable

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from structlog import get_logger

from core.domain.exceptions import DefaultError
from core.utils.streams import format_model_for_sse

_log = get_logger(__name__)


def safe_streaming_response(
    stream_generator: Callable[[], AsyncIterator[BaseModel]],
    media_type: str = "text/event-stream",
) -> StreamingResponse:
    """
    Creates a StreamingResponse with error handling.

    Args:
        stream_generator: A function that returns an async generator of model objects
        media_type: The media type for the response

    Returns:
        A StreamingResponse object
    """

    async def _stream() -> AsyncGenerator[str]:
        try:
            async for item in stream_generator():
                yield format_model_for_sse(item)
        except DefaultError as e:
            if e.capture:
                _log.exception("Received error during streaming", exc_info=e)
            yield format_model_for_sse(e.serialized())
        except Exception as e:  # noqa: BLE001
            _log.exception("Received unexpected error during streaming", exc_info=e)
            yield format_model_for_sse(DefaultError().serialized())

    return StreamingResponse(
        _stream(),
        media_type=media_type,
    )
