import base64
from typing import Any

import pytest

from core.domain.exceptions import InvalidRunOptionsError, UnpriceableRunError
from core.domain.message import File, MessageDeprecated
from core.domain.models import Model
from core.domain.tool import Tool as DomainTool
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.domain.tool_choice import ToolChoice as DomainToolChoice
from core.domain.tool_choice import ToolChoiceFunction
from core.providers._base.provider_error import ModelDoesNotSupportModeError
from core.providers.amazon_bedrock.amazon_bedrock_domain import (
    AmazonBedrockMessage,
    AmazonBedrockSystemMessage,
    BedrockToolConfig,
    CompletionRequest,
    CompletionResponse,
    ContentBlock,
    StreamedResponse,
    Usage,
)


def test_amazonbedrockmessage_from_domain():
    # Test with text content
    text_message = MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello, world!")
    anthropic_message = AmazonBedrockMessage.from_domain(text_message)
    assert len(anthropic_message.content) == 1
    assert anthropic_message.content[0].text == "Hello, world!"
    assert anthropic_message.role == "user"

    # Test with image content
    image_data = base64.b64encode(b"fake_image_data").decode()
    image_message = MessageDeprecated(
        role=MessageDeprecated.Role.USER,
        content="Check this image:",
        files=[File(data=image_data, content_type="image/png")],
    )
    anthropic_message = AmazonBedrockMessage.from_domain(image_message)
    assert len(anthropic_message.content) == 2
    assert anthropic_message.content[0].text == "Check this image:"
    assert anthropic_message.content[1].image
    assert anthropic_message.content[1].image.format == "png"
    assert anthropic_message.content[1].image.source.bytes == image_data
    assert anthropic_message.role == "user"

    # Test with unsupported image format
    with pytest.raises(ModelDoesNotSupportModeError):
        _ = AmazonBedrockMessage.from_domain(
            MessageDeprecated(
                role=MessageDeprecated.Role.USER,
                content="Unsupported image:",
                files=[File(data=image_data, content_type="image/tiff")],
            ),
        )

    # Test assistant message
    assistant_message = MessageDeprecated(role=MessageDeprecated.Role.ASSISTANT, content="I'm here to help!")
    anthropic_message = AmazonBedrockMessage.from_domain(assistant_message)
    assert len(anthropic_message.content) == 1
    assert anthropic_message.content[0].text == "I'm here to help!"
    assert anthropic_message.role == "assistant"


def test_amazonbedrocksystemmessage_from_domain() -> None:
    # Test valid system message
    system_message = MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="You are a helpful assistant.")
    anthropic_system_message = AmazonBedrockSystemMessage.from_domain(system_message)
    assert anthropic_system_message.text == "You are a helpful assistant."

    # Test system message with image (should raise an error)
    image_data = base64.b64encode(b"fake_image_data").decode()
    system_message_with_image = MessageDeprecated(
        role=MessageDeprecated.Role.SYSTEM,
        content="System message with image",
        files=[File(data=image_data, content_type="image/png")],
    )
    with pytest.raises(InvalidRunOptionsError):
        _ = AmazonBedrockSystemMessage.from_domain(system_message_with_image)


@pytest.mark.parametrize(
    ("content", "expected_tokens"),
    [
        (["Hello, world!"], 4),
        (["This is a longer message with multiple words."], 9),
        (["First message", "Second message"], 4),
    ],
)
def test_amazonbedrockmessage_token_count(content: list[str], expected_tokens: int) -> None:
    message = AmazonBedrockMessage(content=[ContentBlock(text=text) for text in content])
    model = Model.CLAUDE_3_5_SONNET_20240620  # Using this as a placeholder model
    assert message.token_count(model) == expected_tokens


def test_amazonbedrockmessage_token_count_with_image() -> None:
    message = AmazonBedrockMessage(
        content=[
            ContentBlock(text="Check this image:"),
            ContentBlock(image=ContentBlock.Image(format="png", source=ContentBlock.Image.Source(bytes="fake_data"))),
        ],
    )
    model = Model.CLAUDE_3_5_SONNET_20240620
    with pytest.raises(UnpriceableRunError, match="Token counting for images is not implemented"):
        _ = message.token_count(model)


@pytest.mark.parametrize(
    ("text", "expected_tokens"),
    [
        ("You are a helpful assistant.", 6),
        ("This is a longer system message with multiple words.", 10),
    ],
)
def test_amazonbedrocksystemmessage_token_count(text: str, expected_tokens: int) -> None:
    system_message = AmazonBedrockSystemMessage(text=text)
    model = Model.CLAUDE_3_5_SONNET_20240620  # Using this as a placeholder model
    assert system_message.token_count(model) == expected_tokens


class TestFileContentBlock:
    def test_from_domain(self) -> None:
        image = File(data=base64.b64encode(b"fake_image_data").decode(), content_type="image/png")
        image_block = ContentBlock.Image.from_domain(image)
        assert image_block.format == "png"
        assert image_block.source.bytes == "ZmFrZV9pbWFnZV9kYXRh"

        assert image.to_url() == "data:image/png;base64,ZmFrZV9pbWFnZV9kYXRh", "sanity"
        assert image_block.to_url() == image.to_url()


class TestAmazonBedrockMessageWithTools:
    def test_from_domain_with_tool_call_request(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Use tool",
            tool_call_requests=[
                ToolCallRequest(
                    id="test_id",
                    tool_name="test_tool",
                    tool_input_dict={"param": "value"},
                ),
            ],
        )
        bedrock_message = AmazonBedrockMessage.from_domain(message)
        assert len(bedrock_message.content) == 2  # text content and tool use
        assert bedrock_message.content[0].text == "Use tool"
        assert bedrock_message.content[1].toolUse is not None
        assert bedrock_message.content[1].toolUse.toolUseId == "test_id"
        assert (
            bedrock_message.content[1].toolUse.name == "test_tool"
        )  # Assuming internal_tool_name_to_native_tool_call returns same name
        assert bedrock_message.content[1].toolUse.input == {"param": "value"}

    def test_from_domain_with_tool_call_result(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.ASSISTANT,
            content="Tool result",
            tool_call_results=[
                ToolCallResult(
                    id="test_id",
                    tool_name="test_tool",
                    tool_input_dict={"param": "value"},
                    result='{"result": "success_value"}',
                ),
            ],
        )
        bedrock_message = AmazonBedrockMessage.from_domain(message)
        assert len(bedrock_message.content) == 2  # text content and tool result
        assert bedrock_message.content[0].text == "Tool result"
        assert bedrock_message.content[1].toolResult is not None
        assert bedrock_message.content[1].toolResult.toolUseId == "test_id"
        assert len(bedrock_message.content[1].toolResult.content) == 1
        assert bedrock_message.content[1].toolResult.content[0].json_content == {"result": "success_value"}

    def test_from_domain_with_non_json_tool_result(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.ASSISTANT,
            content="Tool result",
            tool_call_results=[
                ToolCallResult(
                    id="test_id",
                    tool_name="test_tool",
                    tool_input_dict={"param": "value"},
                    result="plain text result",
                ),
            ],
        )
        bedrock_message = AmazonBedrockMessage.from_domain(message)
        assert len(bedrock_message.content) == 2
        assert bedrock_message.content[1].toolResult is not None
        assert bedrock_message.content[1].toolResult.content[0].json_content == {"result": "plain text result"}

    def test_from_domain_with_invalid_id(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.ASSISTANT,
            content="Tool result",
            tool_call_results=[
                ToolCallResult(
                    id="@whateverIAm",
                    tool_name="test_tool",
                    tool_input_dict={"param": "value"},
                    result="plain text result",
                ),
            ],
        )
        bedrock_message = AmazonBedrockMessage.from_domain(message)
        assert len(bedrock_message.content) == 2
        assert bedrock_message.content[1].toolResult is not None
        assert (
            bedrock_message.content[1].toolResult.toolUseId
            == "b5d2b7dfe4a49cbaf8f3ee7b6b3589703e16d06d4a4f4c73562406a0d205c78b"
        )
        assert bedrock_message.content[1].toolResult.content[0].json_content == {"result": "plain text result"}


class TestBedrockToolConfig:
    def test_from_domain_with_tools(self):
        # Create test tools
        tool1 = DomainTool(
            name="test_tool_1",
            description="Test tool 1 description",
            input_schema={"type": "object", "properties": {"param1": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )
        tool2 = DomainTool(
            name="test_tool_2",
            description="Test tool 2 description",
            input_schema={"type": "object", "properties": {"param2": {"type": "number"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
        )

        # Test with tools but no tool choice
        config = BedrockToolConfig.from_domain([tool1, tool2], None)
        assert config is not None
        assert len(config.tools) == 2
        assert config.tools[0].toolSpec.name == "test_tool_1"
        assert config.tools[0].toolSpec.description == "Test tool 1 description"
        assert config.tools[0].toolSpec.inputSchema.json_schema == {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
        }
        assert config.tools[1].toolSpec.name == "test_tool_2"
        assert config.tools[1].toolSpec.description == "Test tool 2 description"
        assert config.tools[1].toolSpec.inputSchema.json_schema == {
            "type": "object",
            "properties": {"param2": {"type": "number"}},
        }
        assert config.toolChoice is None

        # Test with no tools
        assert BedrockToolConfig.from_domain(None, None) is None

    @pytest.mark.parametrize(
        ("tool_choice", "expected_tool_choice"),
        [
            pytest.param("auto", {"auto": {}, "any": None, "tool": None}, id="auto"),
            pytest.param("required", {"auto": None, "any": {}, "tool": None}, id="required"),
            pytest.param("none", None, id="none"),
            pytest.param(
                ToolChoiceFunction(name="test_tool"),
                {"auto": None, "any": None, "tool": {"name": "test_tool"}},
                id="tool_choice_function",
            ),
        ],
    )
    def test_from_domain_with_tool_choice(
        self,
        tool_choice: DomainToolChoice,
        expected_tool_choice: dict[str, Any] | None,
    ):
        tool = DomainTool(
            name="test_tool",
            description="Test tool description",
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )

        config = BedrockToolConfig.from_domain([tool], tool_choice)
        assert config is not None

        if expected_tool_choice is None:
            assert config.toolChoice is None
        else:
            assert config.toolChoice is not None
            assert config.toolChoice.auto == expected_tool_choice["auto"]
            assert config.toolChoice.any == expected_tool_choice["any"]
            assert config.toolChoice.tool == expected_tool_choice["tool"]

    def test_tool_without_description(self):
        # Test tool with empty description
        tool = DomainTool(
            name="test_tool",
            description="",
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )
        config = BedrockToolConfig.from_domain([tool], None)
        assert config is not None
        assert config.tools[0].toolSpec.description is None

        # Test tool with single character description
        tool = DomainTool(
            name="test_tool",
            description="a",
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )
        config = BedrockToolConfig.from_domain([tool], None)
        assert config is not None
        assert config.tools[0].toolSpec.description is None

        # Test tool with valid description
        tool = DomainTool(
            name="test_tool",
            description="Valid description",
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )
        config = BedrockToolConfig.from_domain([tool], None)
        assert config is not None
        assert config.tools[0].toolSpec.description == "Valid description"


class TestContentBlockThinkingContent:
    def test_thinking_content_creation(self):
        """Test creation of ThinkingContent within ContentBlock."""
        thinking = ContentBlock.ThinkingContent(
            thinking="Let me analyze this step by step...",
            signature="thinking_signature_abc",
        )

        assert thinking.thinking == "Let me analyze this step by step..."
        assert thinking.signature == "thinking_signature_abc"


class TestCompletionRequestThinking:
    def test_completion_request_thinking_enabled(self):
        """Test CompletionRequest with thinking configuration."""
        thinking_config = CompletionRequest.AdditionalModelRequestFields(
            thinking=CompletionRequest.AdditionalModelRequestFields.Thinking(
                type="enabled",
                budget_tokens=1500,
            ),
        )

        request = CompletionRequest(
            system=[],
            messages=[],
            inferenceConfig=CompletionRequest.InferenceConfig(
                maxTokens=4000,
                temperature=0.7,
            ),
            additionalModelRequestFields=thinking_config,
        )

        request_dict = request.model_dump()
        assert request_dict["additionalModelRequestFields"]["thinking"] == {
            "type": "enabled",
            "budget_tokens": 1500,
        }

    def test_completion_request_without_thinking(self):
        """Test CompletionRequest without thinking configuration."""
        request = CompletionRequest(
            system=[],
            messages=[],
            inferenceConfig=CompletionRequest.InferenceConfig(
                maxTokens=4000,
                temperature=0.7,
            ),
        )

        request_dict = request.model_dump()
        assert request_dict["additionalModelRequestFields"] is None


class TestStreamedResponseThinking:
    def test_thinking_delta_creation(self):
        """Test creation of ThinkingDelta in StreamedResponse."""
        reasoning_content = StreamedResponse.Delta.ReasoningContentDelta(
            text="I need to understand the context first...",
        )

        assert reasoning_content.text == "I need to understand the context first..."

    def test_thinking_block_creation(self):
        """Test creation of ThinkingBlock in StreamedResponse."""
        thinking_block = StreamedResponse.Start.ThinkingBlock(
            thinking="Starting to think about this problem...",
        )

        assert thinking_block.thinking == "Starting to think about this problem..."

    def test_thinking_block_without_content(self):
        """Test creation of ThinkingBlock without thinking content."""
        thinking_block = StreamedResponse.Start.ThinkingBlock()

        assert thinking_block.thinking is None

    def test_streamed_response_with_thinking_delta(self):
        """Test StreamedResponse with thinking delta."""
        response = StreamedResponse(
            contentBlockIndex=0,
            delta=StreamedResponse.Delta(
                reasoningContent=StreamedResponse.Delta.ReasoningContentDelta(
                    text="Processing the user's question...",
                ),
            ),
        )

        assert response.contentBlockIndex == 0
        assert response.delta is not None
        assert response.delta.reasoningContent is not None
        assert response.delta.reasoningContent.text == "Processing the user's question..."

    def test_streamed_response_with_thinking_start(self):
        """Test StreamedResponse with thinking start block."""
        response = StreamedResponse(
            contentBlockIndex=0,
            start=StreamedResponse.Start(
                thinking=StreamedResponse.Start.ThinkingBlock(
                    thinking="Beginning reasoning process...",
                ),
            ),
        )

        assert response.contentBlockIndex == 0
        assert response.start is not None
        assert response.start.thinking is not None
        assert response.start.thinking.thinking == "Beginning reasoning process..."

    def test_streamed_response_with_mixed_content(self):
        """Test StreamedResponse with text and thinking deltas."""
        # Test with text delta
        text_response = StreamedResponse(
            contentBlockIndex=0,
            delta=StreamedResponse.Delta(
                text="Here's my answer: ",
            ),
        )

        assert text_response.delta is not None
        assert text_response.delta.text == "Here's my answer: "
        assert text_response.delta.reasoningContent is None

        # Test with thinking delta
        thinking_response = StreamedResponse(
            contentBlockIndex=1,
            delta=StreamedResponse.Delta(
                reasoningContent=StreamedResponse.Delta.ReasoningContentDelta(
                    text="Let me verify this approach...",
                ),
            ),
        )

        assert thinking_response.delta is not None
        assert thinking_response.delta.text is None
        assert thinking_response.delta.reasoningContent is not None
        assert thinking_response.delta.reasoningContent.text == "Let me verify this approach..."


class TestCompletionResponseWithThinking:
    def test_completion_response_with_thinking_content(self):
        """Test CompletionResponse containing thinking content blocks."""
        response = CompletionResponse(
            stopReason="end_turn",
            output=CompletionResponse.Output(
                message=CompletionResponse.Output.Message(
                    role="assistant",
                    content=[
                        ContentBlock(
                            thinking=ContentBlock.ThinkingContent(
                                thinking="I should approach this systematically...",
                                signature="thinking_123",
                            ),
                        ),
                        ContentBlock(text="Based on my analysis, the answer is..."),
                    ],
                ),
            ),
            usage=Usage(inputTokens=100, outputTokens=150, totalTokens=250),
        )

        # Check that thinking content is present
        thinking_blocks = [content for content in response.output.message.content if content.thinking is not None]
        assert len(thinking_blocks) == 1
        assert thinking_blocks[0].thinking is not None
        assert thinking_blocks[0].thinking.thinking == "I should approach this systematically..."
        assert thinking_blocks[0].thinking.signature == "thinking_123"

        # Check that text content is also present
        text_blocks = [content for content in response.output.message.content if content.text is not None]
        assert len(text_blocks) == 1
        assert text_blocks[0].text == "Based on my analysis, the answer is..."

    def test_completion_response_without_thinking(self):
        """Test CompletionResponse without thinking content."""
        response = CompletionResponse(
            stopReason="end_turn",
            output=CompletionResponse.Output(
                message=CompletionResponse.Output.Message(
                    role="assistant",
                    content=[
                        ContentBlock(text="Simple response without thinking."),
                    ],
                ),
            ),
            usage=Usage(inputTokens=50, outputTokens=75, totalTokens=125),
        )

        # Check that no thinking content is present
        thinking_blocks = [content for content in response.output.message.content if content.thinking is not None]
        assert len(thinking_blocks) == 0

        # Check that text content is present
        text_blocks = [content for content in response.output.message.content if content.text is not None]
        assert len(text_blocks) == 1
        assert text_blocks[0].text == "Simple response without thinking."
