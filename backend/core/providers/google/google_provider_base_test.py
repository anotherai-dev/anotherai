from unittest.mock import Mock

import httpx
import pytest

from core.domain.tool_call import ToolCallRequest
from core.providers._base.provider_error import ProviderInvalidFileError
from core.providers.google.google_provider_base import GoogleProviderBase
from core.providers.google.google_provider_domain import Candidate, CompletionResponse, Content, Part, UsageMetadata


def test_extract_native_tool_calls_empty_response() -> None:
    response = CompletionResponse(
        candidates=[
            Candidate(
                content=None,
            ),
        ],
        usageMetadata=UsageMetadata(),
    )
    result = GoogleProviderBase._extract_native_tool_calls(response)  # pyright: ignore[reportPrivateUsage]
    assert result == []


def test_extract_native_tool_calls_no_function_calls() -> None:
    response = CompletionResponse(
        candidates=[
            Candidate(
                content=Content(
                    role="model",
                    parts=[Part(text="some text")],
                ),
            ),
        ],
        usageMetadata=UsageMetadata(),
    )
    result = GoogleProviderBase._extract_native_tool_calls(response)  # pyright: ignore[reportPrivateUsage]
    assert result == []


def test_extract_native_tool_calls_with_function_calls() -> None:
    response = CompletionResponse(
        candidates=[
            Candidate(
                content=Content(
                    role="model",
                    parts=[
                        Part(
                            functionCall=Part.FunctionCall(
                                name="browser-text",
                                args={"url": "https://example.com"},
                            ),
                        ),
                        Part(
                            functionCall=Part.FunctionCall(
                                name="external-tool",
                                args={"param1": "value1"},
                            ),
                        ),
                    ],
                ),
            ),
        ],
        usageMetadata=UsageMetadata(),
    )
    result = GoogleProviderBase._extract_native_tool_calls(response)  # pyright: ignore[reportPrivateUsage]
    assert result == [
        ToolCallRequest(
            tool_name="@browser-text",
            tool_input_dict={"url": "https://example.com"},
        ),
        ToolCallRequest(
            tool_name="external-tool",
            tool_input_dict={"param1": "value1"},
        ),
    ]


def test_extract_native_tool_calls_missing_tool_name() -> None:
    response = CompletionResponse(
        candidates=[
            Candidate(
                content=Content(
                    role="model",
                    parts=[
                        Part(
                            functionCall=Part.FunctionCall(
                                name="non-existent-tool",
                                args={},
                            ),
                        ),
                    ],
                ),
            ),
        ],
        usageMetadata=UsageMetadata(),
    )
    result = GoogleProviderBase._extract_native_tool_calls(response)  # pyright: ignore[reportPrivateUsage]
    assert result == [
        ToolCallRequest(
            tool_name="non-existent-tool",
            tool_input_dict={},
        ),
    ]


@pytest.mark.parametrize(
    "error_message",
    [
        "Failed to fetch the file from the provided URL: url_error-error_not_found. Please check if the URL is accessible.",
        "Request failed due to url_timeout-timeout_fetchproxy. The server did not respond within the expected time.",
        "Unable to reach the provided URL: url_unreachable-unreachable_no_response. Please verify the URL is correct.",
        "The request was rejected: url_rejected-rejected_rpc_app_error. The server refused the connection.",
        "File upload failed: base64 decoding failed. The provided data is not valid base64.",
        "Processing failed: the document has no pages to analyze.",
        "Image processing error: unable to process input image. The image format may be unsupported or corrupted.",
        "Network error: url_unreachable-unreachable_5xx. The server returned an error status.",
        "Access denied: url_rejected by the target server.",
        "The requested URL is blocked: url_roboted. Access is restricted by robots.txt.",
        "File retrieval failed. Please ensure the url is valid and accessible from our servers.",
        "Unable to submit request because it has a mimeType parameter with value application/msword, which is not supported. Update the mimeType and try again. Learn more: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini",
    ],
)
def test_handle_invalid_argument_raises_provider_invalid_file_error(error_message: str) -> None:
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 400

    with pytest.raises(ProviderInvalidFileError):
        GoogleProviderBase._handle_invalid_argument(error_message, mock_response)  # pyright: ignore[reportPrivateUsage]
