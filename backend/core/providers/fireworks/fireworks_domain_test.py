import pytest

from core.domain.exceptions import UnpriceableRunError
from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.models import Model
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.providers.fireworks.fireworks_domain import (
    FireworksAIError,
    FireworksMessage,
    FireworksToolCall,
    FireworksToolCallFunction,
    FireworksToolMessage,
    ImageContent,
    StreamedResponse,
    TextContent,
)


def test_streamed_response_init():
    streamed = b'{"id":"chatcmpl-9iYcb4Ciq3vzot8MbmzePysMilDIT","object":"chat.completion.chunk","created":1720406545,"model":"gpt-4o-2024-05-13","system_fingerprint":"fp_d576307f90","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}'
    raw = StreamedResponse.model_validate_json(streamed)
    assert raw.choices[0].delta.content == ""


def test_streamed_response_final():
    streamed = b'{"id":"chatcmpl-9iYe8rHP2EGOXWywPICQw1pnrrCAz","object":"chat.completion.chunk","created":1720406640,"model":"gpt-4o-2024-05-13","system_fingerprint":"fp_4008e3b719","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}'
    raw = StreamedResponse.model_validate_json(streamed)
    assert raw.choices[0].delta.content == ""


class TestFireworksAIError:
    @pytest.mark.parametrize(
        "payload",
        [
            """{"error":{"message":"'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.","type":"invalid_request_error","param":"messages","code":null}}""",
        ],
    )
    def test_error(self, payload: str):
        assert FireworksAIError.model_validate_json(payload)

    def test_error_with_string_payload(self):
        payload = '{"error":"The account does not have a default payment method"}'
        error = FireworksAIError.model_validate_json(payload)
        assert error.error.message == "The account does not have a default payment method"


class TestFireworksMessageTokenCount:
    def test_token_count_for_text_message(self):
        message = FireworksMessage(content="Hello, world!", role="user")
        assert message.token_count(Model.QWEN_QWQ_32B_PREVIEW) == 4

    def test_token_count_for_text_content_message(self):
        message = FireworksMessage(
            content=[TextContent(text="Hello, world!"), TextContent(text="Hello, world!")],
            role="user",
        )
        assert message.token_count(Model.QWEN_QWQ_32B_PREVIEW) == 8

    def test_token_count_for_image_message_raises(self):
        message = FireworksMessage(
            content=[ImageContent(image_url=ImageContent.URL(url="https://example.com/image.png"))],
            role="user",
        )
        with pytest.raises(UnpriceableRunError):
            message.token_count(Model.QWEN_QWQ_32B_PREVIEW)


class TestFireworksMessageFromDomain:
    def test_text_before_files(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Hello world",
            files=[File(url="http://localhost/hello", content_type="image/png")],
        )

        fireworks_message = FireworksMessage.from_domain(message)
        assert isinstance(fireworks_message.content, list)
        assert len(fireworks_message.content) == 2
        assert isinstance(fireworks_message.content[0], TextContent)
        assert fireworks_message.content[0].text == "Hello world"
        assert isinstance(fireworks_message.content[1], ImageContent)


class TestFireworksMessageToolCalls:
    def test_from_domain_with_files_tool_calls(self) -> None:
        # Create a Message instance with a file and simulate tool call output
        file = File(url="http://localhost/hello", content_type="image/png")
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Original content",
            files=[file],
        )
        fireworks_message = FireworksMessage.from_domain(message)
        assert fireworks_message.role == "user"
        assert isinstance(fireworks_message.content, list)
        assert len(fireworks_message.content) == 2
        text_content = fireworks_message.content[0]
        image_content = fireworks_message.content[1]
        assert isinstance(text_content, TextContent)
        assert text_content.text == "Original content"
        assert isinstance(image_content, ImageContent)


class TestFireworksToolMessage:
    def test_from_domain_with_tool_call_results(self) -> None:
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Test content",
            tool_call_results=[
                ToolCallResult(
                    id="test_id_1",
                    tool_name="test_tool",
                    tool_input_dict={"key": "value"},
                    result={"key": "value"},
                ),
                ToolCallResult(
                    id="test_id_2",
                    tool_name="test_tool",
                    tool_input_dict={"key": "value"},
                    result="string result",
                ),
            ],
        )

        tool_messages = FireworksToolMessage.from_domain(message)
        assert len(tool_messages) == 2
        assert tool_messages[0].tool_call_id == "test_id_1"
        assert tool_messages[0].content == "{'key': 'value'}"
        assert tool_messages[1].tool_call_id == "test_id_2"
        assert tool_messages[1].content == "string result"

    def test_from_domain_without_tool_call_results(self) -> None:
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Test content",
        )

        tool_messages = FireworksToolMessage.from_domain(message)
        assert len(tool_messages) == 0


class TestFireworksMessageNativeToolCalls:
    def test_from_domain_with_tool_call_requests(self) -> None:
        message = MessageDeprecated(
            role=MessageDeprecated.Role.ASSISTANT,
            content="Test content",
            tool_call_requests=[
                ToolCallRequest(
                    id="test_id_1",
                    tool_name="test_tool",
                    tool_input_dict={"key": "value"},
                ),
            ],
        )

        fireworks_message = FireworksMessage.from_domain(message)
        assert fireworks_message == FireworksMessage(
            role="assistant",
            content=[TextContent(text="Test content")],
            tool_calls=[
                FireworksToolCall(
                    id="test_id_1",
                    type="function",
                    function=FireworksToolCallFunction(
                        name="test_tool",
                        arguments='{"key": "value"}',
                    ),
                ),
            ],
        )


class TestStreamedToolCall:
    def test_streamed_response_with_tool_call(self) -> None:
        streamed = b'{"id":"test-id","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"test_id_1","type":"function","function":{"name":"test_tool","arguments":"{\\"key\\": \\"value\\"}"}}]}}]}'
        raw = StreamedResponse.model_validate_json(streamed)
        assert raw.choices[0].delta.tool_calls is not None
        assert len(raw.choices[0].delta.tool_calls) == 1
        assert raw.choices[0].delta.tool_calls[0].index == 0
        assert raw.choices[0].delta.tool_calls[0].id == "test_id_1"
        assert raw.choices[0].delta.tool_calls[0].type == "function"
        assert raw.choices[0].delta.tool_calls[0].function.name == "test_tool"
        assert raw.choices[0].delta.tool_calls[0].function.arguments == '{"key": "value"}'

    def test_streamed_response_with_partial_tool_call(self) -> None:
        streamed = b'{"id":"test-id","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"test_id_1","type":"function","function":{"name":"test_tool","arguments":"{\\"key"}}]}}]}'
        raw = StreamedResponse.model_validate_json(streamed)
        assert raw.choices[0].delta.tool_calls is not None
        assert len(raw.choices[0].delta.tool_calls) == 1
        assert raw.choices[0].delta.tool_calls[0].index == 0
        assert raw.choices[0].delta.tool_calls[0].id == "test_id_1"
        assert raw.choices[0].delta.tool_calls[0].type == "function"
        assert raw.choices[0].delta.tool_calls[0].function.name == "test_tool"
        assert raw.choices[0].delta.tool_calls[0].function.arguments == '{"key'
