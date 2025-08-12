import pytest

from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.tool_call import ToolCallRequest
from core.providers.mistral.mistral_domain import (
    CompletionChunk,
    DocumentURLChunk,
    ImageURLChunk,
    MistralAIMessage,
    MistralError,
    TextChunk,
)


def test_streamed_response_init() -> None:
    # Given
    streamed = b'{"id":"chatcmpl-9iYcb4Ciq3vzot8MbmzePysMilDIT","object":"chat.completion.chunk","created":1720406545,"model":"gpt-4o-2024-05-13","system_fingerprint":"fp_d576307f90","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}'

    # When
    raw = CompletionChunk.model_validate_json(streamed)

    # Then
    assert raw.choices
    assert raw.choices[0].delta
    assert raw.choices[0].delta.content == ""


def test_streamed_response_final() -> None:
    # Given
    streamed = b'{"id":"chatcmpl-9iYe8rHP2EGOXWywPICQw1pnrrCAz","object":"chat.completion.chunk","created":1720406640,"model":"gpt-4o-2024-05-13","system_fingerprint":"fp_4008e3b719","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}'

    # When
    raw = CompletionChunk.model_validate_json(streamed)

    # Then
    assert raw.choices
    assert raw.choices[0].delta
    assert raw.choices[0].delta.content is None
    assert raw.choices[0].finish_reason == "stop"


@pytest.mark.parametrize(
    "payload",
    [
        """{"msg":"hello"}""",
        """{"message":"hello"}""",
        """{"message":"hello","type":"invalid_request_error"}""",
    ],
)
def test_error(payload: str) -> None:
    # When
    val = MistralError.model_validate_json(payload)

    # Then
    assert val.message == "hello"


# TODO: add tests for token count if we ever count token properly for mistral


class TestMistralAIMessage:
    def test_from_domain_simple_message(self) -> None:
        # Given
        message = MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello world")

        # When
        result = MistralAIMessage.from_domain(message)

        # Then
        assert result.role == "user"
        assert result.content == "Hello world"
        assert result.tool_calls is None

    def test_from_domain_with_image(self) -> None:
        # Given
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Check this image",
            files=[File(url="https://example.com/image.jpg", content_type="image/jpeg")],
        )

        # When
        result = MistralAIMessage.from_domain(message)

        # Then
        assert result.role == "user"
        assert isinstance(result.content, list)
        assert len(result.content) == 2
        assert isinstance(result.content[0], TextChunk)
        assert result.content[0].text == "Check this image"
        assert isinstance(result.content[1], ImageURLChunk)
        assert result.content[1].image_url.url == "https://example.com/image.jpg"

    def test_from_domain_with_document(self) -> None:
        # Given
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Check this document",
            files=[File(url="https://example.com/document.pdf", content_type="application/pdf")],
        )

        # When
        result = MistralAIMessage.from_domain(message)

        # Then
        assert result.role == "user"
        assert isinstance(result.content, list)
        assert len(result.content) == 2
        assert isinstance(result.content[0], TextChunk)
        assert result.content[0].text == "Check this document"
        assert isinstance(result.content[1], DocumentURLChunk)
        assert result.content[1].document_url == "https://example.com/document.pdf"

    def test_from_domain_with_tool_calls(self) -> None:
        # Given
        message = MessageDeprecated(
            role=MessageDeprecated.Role.ASSISTANT,
            content="Using calculator",
            tool_call_requests=[
                ToolCallRequest(
                    id="123",
                    tool_name="calculator",
                    tool_input_dict={"operation": "add", "numbers": [1, 2]},
                ),
            ],
        )

        # When
        result = MistralAIMessage.from_domain(message)

        # Then
        assert result.role == "assistant"
        assert result.content == "Using calculator"
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].function.name == "calculator"
        assert result.tool_calls[0].function.arguments == {"operation": "add", "numbers": [1, 2]}
