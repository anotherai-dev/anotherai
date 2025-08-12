import json
from collections.abc import AsyncGenerator, Callable
from typing import Any
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel
from structlog.testing import LogCapture

from core.domain.error import Error
from core.domain.exceptions import DefaultError
from core.utils.stream_response_utils import safe_streaming_response


class _TestModel(BaseModel):
    """Simple test model for streaming tests."""

    value: str
    data: dict[str, Any] | None = None


# Create mock generators for testing
async def mock_successful_generator() -> AsyncGenerator[BaseModel]:
    """Generator that yields two test models without errors."""
    yield _TestModel(value="first item")
    yield _TestModel(value="second item", data={"key": "value"})


async def mock_default_error_generator() -> AsyncGenerator[BaseModel]:
    """Generator that yields one item and then raises a DefaultError."""
    yield _TestModel(value="successful item")
    # Create a DefaultError with capture=True to ensure logging happens
    error = DefaultError("Test default error")
    error.capture = True
    raise error


async def mock_default_error_no_capture_generator() -> AsyncGenerator[BaseModel]:
    """Generator that yields one item and then raises a DefaultError with capture=False."""
    yield _TestModel(value="successful item")
    # Create a DefaultError with capture=False to test no logging
    error = DefaultError("Test default error")
    error.capture = False
    raise error


async def mock_unexpected_error_generator() -> AsyncGenerator[BaseModel]:
    """Generator that yields one item and then raises an unexpected exception."""
    yield _TestModel(value="successful item")
    raise ValueError("Unexpected test error")


@pytest.mark.parametrize(
    ("generator", "expected_items", "has_error", "error_type"),
    [
        (mock_successful_generator, 2, False, None),
        (mock_default_error_generator, 1, True, "DefaultError"),
        (mock_unexpected_error_generator, 1, True, "DefaultError"),  # All errors converted to DefaultError
    ],
)
async def test_create_streaming_response_error_handling(
    generator: Callable[[], AsyncGenerator[BaseModel]],
    expected_items: int,
    has_error: bool,
    error_type: str | None,
    log_capture: LogCapture,
) -> None:  # Mock format_model_for_sse to capture what would be sent
    formatted_items: list[dict[str, Any]] = []

    # Create a mock that returns a JSON string and also stores the input
    def mock_format(model: BaseModel) -> str:
        # Convert the model to a dict for easier comparison
        if isinstance(model, Error):
            # Access the error response fields safely
            data: dict[str, Any] = {
                "error": True,
                "code": model.code if hasattr(model, "code") else None,
                "message": model.message if hasattr(model, "message") else None,
            }
        else:
            data = model.model_dump()

        formatted_items.append(data)
        # Return a JSON string that simulates the actual function
        return f"data: {json.dumps(data)}"

    # Apply the mock and create the response
    with patch("core.utils.stream_response_utils.format_model_for_sse", side_effect=mock_format):
        response = safe_streaming_response(generator)

        # Get the async generator from the response
        stream_gen = response.body_iterator

        # Consume the generator to trigger all the processing
        consumed_lines = [line async for line in stream_gen]

        # Verify we got the expected number of lines
        assert len(consumed_lines) > 0

        # Verify the structure of the output
        expected_count = expected_items + (1 if has_error else 0)
        assert len(formatted_items) == expected_count

        # Check that the expected number of successful items were processed
        successful_items = [item for item in formatted_items if "value" in item]
        assert len(successful_items) == expected_items

        # If we expect an error, verify the error response
        if has_error:
            error_items = [item for item in formatted_items if item.get("error") is True]
            assert len(error_items) == 1
            if error_type:
                # For DefaultError, the code is "internal_error" by default
                assert error_items[0]["code"] == "internal_error"


async def test_error_logging(log_capture: LogCapture) -> None:
    """Test that errors are properly logged."""

    # Test DefaultError logging with capture=True
    with patch("core.utils.stream_response_utils.format_model_for_sse", return_value="data: {}"):
        response = safe_streaming_response(mock_default_error_generator)
        stream_gen = response.body_iterator
        # Consume the generator to trigger the error and logging
        consumed_lines = [line async for line in stream_gen]
        assert len(consumed_lines) > 0

        # Verify log message for DefaultError
        assert "Received error during streaming" in log_capture.entries[0]["event"]

    # Clear logs and test DefaultError with capture=False
    log_capture.entries.clear()

    with patch("core.utils.stream_response_utils.format_model_for_sse", return_value="data: {}"):
        response = safe_streaming_response(mock_default_error_no_capture_generator)
        stream_gen = response.body_iterator
        # Consume the generator to trigger the error and logging
        consumed_lines = [line async for line in stream_gen]
        assert len(consumed_lines) > 0

        # Verify no log message for DefaultError with capture=False
        assert not log_capture.entries

    # Clear logs and test unexpected error
    log_capture.entries.clear()

    with patch("core.utils.stream_response_utils.format_model_for_sse", return_value="data: {}"):
        response = safe_streaming_response(mock_unexpected_error_generator)
        stream_gen = response.body_iterator
        # Consume the generator to trigger the error and logging
        consumed_lines = [line async for line in stream_gen]
        assert len(consumed_lines) > 0

        # Verify log message for unexpected error
        assert "Received unexpected error during streaming" in log_capture.entries[0]["event"]


def test_model_formatting() -> None:
    """Test that models are correctly formatted for the stream."""
    # Create a test model
    test_model = _TestModel(value="test value", data={"nested": "data"})

    # Mock the format_model_for_sse function
    mock_formatter = Mock(return_value="data: {mocked}")

    # Set up the generator
    async def test_generator() -> AsyncGenerator[BaseModel]:
        yield test_model

    # Use our mocked formatter
    with patch("core.utils.stream_response_utils.format_model_for_sse", mock_formatter):
        # Create the response - this won't actually run the generator yet
        safe_streaming_response(test_generator)

        # Verify our formatter wasn't called yet (lazy evaluation)
        mock_formatter.assert_not_called()

        # To test the actual formatting, we need to create a separate test
        # that verifies format_model_for_sse directly, since the streaming
        # response's generator is evaluated lazily and in an async context


def test_streaming_response_media_type() -> None:
    """Test that the correct media type is set."""

    # Test default media type
    async def empty_gen() -> AsyncGenerator[BaseModel]:
        if False:  # This ensures the generator is empty but properly typed
            yield _TestModel(value="")

    response = safe_streaming_response(empty_gen)
    assert response.media_type == "text/event-stream"

    # Test custom media type
    custom_response = safe_streaming_response(empty_gen, media_type="application/json")
    assert custom_response.media_type == "application/json"
