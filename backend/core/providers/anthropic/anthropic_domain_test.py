import pytest

from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.providers._base.provider_error import (
    MaxTokensExceededError,
    ProviderBadRequestError,
    ProviderError,
    ProviderInternalError,
    UnknownProviderError,
)
from core.providers.anthropic.anthropic_domain import (
    AnthropicMessage,
    CompletionChunk,
    CompletionRequest,
    ErrorDetails,
    ImageContent,
    SignatureDelta,
    TextContent,
    ThinkingDelta,
    ToolResultContent,
    ToolUseContent,
    Usage,
)


def test_anthropic_message_from_domain_user() -> None:
    domain_message = MessageDeprecated(
        role=MessageDeprecated.Role.USER,
        content="Hello, how are you?",
    )

    anthropic_message = AnthropicMessage.from_domain(domain_message)

    assert anthropic_message.role == "user"
    assert anthropic_message.content[0].type == "text"
    assert anthropic_message.content[0].text == "Hello, how are you?"


def test_anthropic_message_from_domain_assistant() -> None:
    domain_message = MessageDeprecated(
        role=MessageDeprecated.Role.ASSISTANT,
        content="I'm doing well, thank you!",
    )

    anthropic_message = AnthropicMessage.from_domain(domain_message)

    assert anthropic_message.role == "assistant"
    assert anthropic_message.content[0].type == "text"
    assert anthropic_message.content[0].text == "I'm doing well, thank you!"


def test_anthropic_message_from_domain_text_before_files() -> None:
    message = MessageDeprecated(
        role=MessageDeprecated.Role.USER,
        content="Hello world",
        files=[File(data="test_data", content_type="image/png")],
    )

    anthropic_message = AnthropicMessage.from_domain(message)
    assert len(anthropic_message.content) == 2
    assert isinstance(anthropic_message.content[0], TextContent)
    assert anthropic_message.content[0].text == "Hello world"
    assert isinstance(anthropic_message.content[1], ImageContent)


def test_anthropic_message_from_domain_with_tool_call_requests() -> None:
    message = MessageDeprecated(
        role=MessageDeprecated.Role.ASSISTANT,
        content="Let me check the weather for you.",
        tool_call_requests=[
            ToolCallRequest(
                id="weather_1",
                tool_name="WeatherCheckTask",
                tool_input_dict={"location": {"latitude": 48.8566, "longitude": 2.3522}},
            ),
        ],
    )

    anthropic_message = AnthropicMessage.from_domain(message)
    assert anthropic_message == AnthropicMessage(
        role="assistant",
        content=[
            TextContent(type="text", text="Let me check the weather for you."),
            ToolUseContent(
                type="tool_use",
                id="weather_1",
                name="WeatherCheckTask",
                input={"location": {"latitude": 48.8566, "longitude": 2.3522}},
            ),
        ],
    )


def test_anthropic_message_from_domain_with_tool_call_results() -> None:
    message = MessageDeprecated(
        role=MessageDeprecated.Role.USER,
        content="Here's what I found:",
        tool_call_results=[
            ToolCallResult(
                id="weather_1",
                tool_name="WeatherCheckTask",
                tool_input_dict={"location": {"latitude": 48.8566, "longitude": 2.3522}},
                result={"temperature": 20, "condition": "sunny"},
                error=None,
            ),
        ],
    )

    anthropic_message = AnthropicMessage.from_domain(message)
    assert anthropic_message == AnthropicMessage(
        role="user",
        content=[
            TextContent(type="text", text="Here's what I found:"),
            ToolResultContent(
                type="tool_result",
                tool_use_id="weather_1",
                content=str({"temperature": 20, "condition": "sunny"}),
            ),
        ],
    )


def test_anthropic_message_from_domain_with_tool_call_error() -> None:
    message = MessageDeprecated(
        role=MessageDeprecated.Role.USER,
        content="I encountered an error:",
        tool_call_results=[
            ToolCallResult(
                id="weather_1",
                tool_name="WeatherCheckTask",
                tool_input_dict={"location": {"latitude": 48.8566, "longitude": 2.3522}},
                result=None,
                error="API unavailable",
            ),
        ],
    )

    anthropic_message = AnthropicMessage.from_domain(message)
    assert anthropic_message == AnthropicMessage(
        role="user",
        content=[
            TextContent(type="text", text="I encountered an error:"),
            ToolResultContent(
                type="tool_result",
                tool_use_id="weather_1",
                content="Error: API unavailable",
            ),
        ],
    )


class TestCompletionRequestThinking:
    def test_completion_request_thinking_enabled(self) -> None:
        """Test CompletionRequest with thinking enabled."""
        thinking_config = CompletionRequest.Thinking(
            type="enabled",
            budget_tokens=1000,
        )

        request = CompletionRequest(
            messages=[],
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7,
            stream=False,
            thinking=thinking_config,
        )

        request_dict = request.model_dump()
        assert request_dict["thinking"] == {
            "type": "enabled",
            "budget_tokens": 1000,
        }

    def test_completion_request_without_thinking(self) -> None:
        """Test CompletionRequest without thinking configuration."""
        request = CompletionRequest(
            messages=[],
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7,
            stream=False,
        )

        request_dict = request.model_dump()
        assert request_dict["thinking"] is None


class TestErrorDetails:
    @pytest.mark.parametrize(
        ("message", "expected_error_cls", "expected_capture"),
        [
            pytest.param("Invalid base64 data", ProviderBadRequestError, True, id="invalid_base64_data"),
            pytest.param("Image exceeds", ProviderBadRequestError, False, id="image_exceeds"),
            pytest.param(
                "Image does not match the provided media type",
                ProviderBadRequestError,
                False,
                id="image_does_not_match_media_type",
            ),
            pytest.param("Prompt is too long", MaxTokensExceededError, False, id="prompt_is_too_long"),
            pytest.param(
                "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.",
                ProviderInternalError,
                True,
                id="credit_balance_too_low",
            ),
            # Make sure we always default to an unknown provider error
            pytest.param("whatever blabla", UnknownProviderError, True, id="unknown_error"),
        ],
    )
    def test_invalid_request_error_to_domain(
        self,
        message: str,
        expected_error_cls: type[ProviderError],
        expected_capture: bool,
    ) -> None:
        error_details = ErrorDetails(message=message, type="invalid_request_error")
        error = error_details.to_domain(None)
        assert isinstance(error, expected_error_cls)
        assert error.capture == expected_capture


class TestCompletionChunk:
    def test_message_start(self) -> None:
        val = CompletionChunk.model_validate(
            {
                "type": "message_start",
                "message": {
                    "id": "msg_01LfyeXJLvnwgEW9d9G6QF6D",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-3-5-sonnet-20241022",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": 717,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "output_tokens": 1,
                    },
                },
            },
        )
        assert val.message
        assert val.message.usage == Usage(
            input_tokens=717,
            output_tokens=1,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )


class TestCompletionChunkToParsedResponse:
    def test_thinking(self):
        chunk = CompletionChunk(
            type="content_block_delta",
            index=0,
            delta=ThinkingDelta(
                type="thinking_delta",
                thinking="I need to analyze this request...",
            ),
        )
        parsed_response = chunk.to_parsed_response()
        assert parsed_response.reasoning == "I need to analyze this request..."

    def test_signature(self):
        # Create a chunk with signature delta
        chunk = CompletionChunk(
            type="content_block_delta",
            index=0,
            delta=SignatureDelta(
                type="signature_delta",
                signature="sig_456",
            ),
        )
        parsed_response = chunk.to_parsed_response()
        assert parsed_response.reasoning is None


class TestContentFromDomain:
    def test_content_from_domain_image(self) -> None:
        file = File(data="test_data", content_type="image/png")
        content = AnthropicMessage.content_from_domain(file)
        assert content.type == "image"
        assert content.source.type == "base64"
        assert content.source.media_type == "image/png"
        assert content.source.data == "test_data"

    def test_image_jpg(self) -> None:
        # image/jpg should be converted to image/jpeg
        file = File(data="test_data", content_type="image/jpg")
        content = AnthropicMessage.content_from_domain(file)
        assert content.type == "image"
        assert content.source.type == "base64"
        assert content.source.media_type == "image/jpeg"
        assert content.source.data == "test_data"
