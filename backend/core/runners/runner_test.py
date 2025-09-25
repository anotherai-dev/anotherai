# pyright: reportPrivateUsage=false

import base64
from unittest.mock import MagicMock

import pytest

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.file import File
from core.domain.message import Message, MessageContent
from core.domain.version import Version
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.runners.runner import Runner
from core.utils.templates import TemplateManager


@pytest.fixture
def template_manager():
    """Create a mock template manager."""
    return TemplateManager()


@pytest.fixture
def provider_factory():
    """Create a mock provider factory."""
    return MagicMock(spec=AbstractProviderFactory)


@pytest.fixture
def runner(provider_factory):
    """Create a Runner instance for testing."""
    return Runner(
        agent=Agent(id="test-agent", uid=1),
        tenant_slug="test-tenant",
        custom_configs=None,
        version=Version(id="test-version", prompt=[]),
        metadata=None,
        metric_tags=None,
        provider_factory=provider_factory,
        timeout=30.0,
        use_fallback="never",
        max_tool_call_iterations=10,
    )


class TestBuildMessages:
    async def test_files_in_input_messages(self, runner: Runner):
        """Check that all files are properly sanitized"""
        # Create test data with multiple file types
        image_data = base64.b64encode(b"fake_image_data").decode()
        pdf_data = base64.b64encode(b"fake_pdf_data").decode()

        # Create messages with various file types
        messages = [
            Message(
                role="user",
                content=[
                    MessageContent(text="Here's an image"),
                    MessageContent(file=File(url="https://example.com/image.png")),
                ],
            ),
            Message(
                role="user",
                content=[
                    MessageContent(file=File(data=image_data, content_type="image/jpeg")),
                ],
            ),
            Message(
                role="assistant",
                content=[
                    MessageContent(text="I see the image"),
                ],
            ),
            Message(
                role="user",
                content=[
                    MessageContent(file=File(data=pdf_data, content_type="application/pdf")),
                    MessageContent(text="And here's a PDF"),
                ],
            ),
        ]

        # Create agent input with messages
        agent_input = AgentInput(messages=messages)

        # Call _build_messages without mocking
        result = await runner._build_messages(agent_input)

        # Verify that all files in the result are sanitized
        # (sanitize is called in-place during build_messages)
        file_count = 0
        for message in result:
            for content in message.content:
                if content.file:
                    file_count += 1
                    # Verify file has been processed
                    assert content.file is not None
                    # If URL-based, content_type should be set
                    if content.file.url and not content.file.data:
                        assert content.file.content_type is not None

        # Should have all 3 files
        assert file_count == 3

        # Verify the result includes all messages
        assert len(result) == len(messages)

    async def test_files_in_input_variables(self, runner: Runner):
        """Check that all files are properly sanitized when using template variables"""
        # Create a version with prompt templates that use variables
        prompt_messages = [
            Message(
                role="system",
                content=[MessageContent(text="System prompt with {{variable}}")],
            ),
            Message(
                role="user",
                content=[
                    MessageContent(text="Analyze this: {{description}}"),
                    MessageContent(file=File(url="{{image_url}}")),
                ],
            ),
        ]

        runner._version.prompt = prompt_messages

        # Create agent input with variables but no messages
        agent_input = AgentInput(
            variables={
                "variable": "test value",
                "description": "A test image",
                "image_url": "https://example.com/test.jpg",
            },
        )

        # Call _build_messages without mocking
        result = await runner._build_messages(agent_input)

        # Verify the prompt was rendered with variables
        assert len(result) == 2

        # Check system message
        assert result[0].role == "system"
        assert result[0].content[0].text == "System prompt with test value"

        # Check user message
        assert result[1].role == "user"
        assert result[1].content[0].text == "Analyze this: A test image"

        # Check that the file URL was rendered and sanitized
        assert result[1].content[1].file is not None
        assert result[1].content[1].file.url == "https://example.com/test.jpg"
        # File should be sanitized (content_type should be set)
        assert result[1].content[1].file.content_type is not None

    async def test_combines_prompt_and_input_messages(self, runner: Runner):
        """Test that prompt messages and input messages are properly combined"""
        # Set up prompt messages
        prompt_messages = [
            Message(
                role="system",
                content=[MessageContent(text="You are a helpful assistant")],
            ),
        ]
        runner._version.prompt = prompt_messages

        # Create input messages
        input_messages = [
            Message(
                role="user",
                content=[MessageContent(text="Hello, can you help me?")],
            ),
        ]

        agent_input = AgentInput(
            messages=input_messages,
            variables={"name": "Test User"},
        )

        # Call _build_messages without mocking
        result = await runner._build_messages(agent_input)

        # Should have both rendered prompt and input messages
        assert len(result) == 2

        # First should be the system message from prompt
        assert result[0].role == "system"
        assert result[0].content[0].text == "You are a helpful assistant"

        # Second should be the user message from input
        assert result[1].role == "user"
        assert result[1].content[0].text == "Hello, can you help me?"

    async def test_no_prompt_no_variables(self, runner: Runner):
        """Test behavior when there's no prompt and no variables"""
        # Ensure no prompt is set
        runner._version.prompt = []

        # Create input with just messages
        input_messages = [
            Message(
                role="user",
                content=[
                    MessageContent(text="Simple message"),
                    MessageContent(file=File(url="https://example.com/file.txt")),
                ],
            ),
        ]

        agent_input = AgentInput(messages=input_messages)

        # Call _build_messages without mocking
        result = await runner._build_messages(agent_input)

        # Should return just the input messages
        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].content[0].text == "Simple message"

        # Files should still be sanitized
        assert result[0].content[1].file is not None
        assert result[0].content[1].file.url == "https://example.com/file.txt"
        # File should be sanitized
        assert result[0].content[1].file.content_type is not None

    async def test_multiple_files_sanitization(self, runner: Runner):
        """Test that multiple files in a single message are all sanitized"""
        # Create a message with multiple files
        file1_data = base64.b64encode(b"file1").decode()
        file2_data = base64.b64encode(b"file2").decode()

        messages = [
            Message(
                role="user",
                content=[
                    MessageContent(text="Here are multiple files:"),
                    MessageContent(file=File(url="https://example.com/doc1.pdf")),
                    MessageContent(file=File(data=file1_data, content_type="image/png")),
                    MessageContent(file=File(url="https://example.com/doc2.txt")),
                    MessageContent(file=File(data=file2_data, content_type="audio/wav")),
                ],
            ),
        ]

        agent_input = AgentInput(messages=messages)

        # Call _build_messages without mocking
        result = await runner._build_messages(agent_input)

        # Verify text content
        assert result[0].content[0].text == "Here are multiple files:"

        # Count and verify files to ensure all are present and sanitized
        file_count = 0
        for message in result:
            for content in message.content:
                if content.file:
                    file_count += 1
                    assert content.file is not None
                    # URL-based files should have content_type set after sanitization
                    if content.file.url and not content.file.data:
                        assert content.file.content_type is not None
                    # Data-based files should retain their content_type
                    if content.file.data:
                        assert content.file.content_type in ["image/png", "audio/wav"]

        assert file_count == 4  # Should have all 4 files

    async def test_empty_input(self, runner: Runner):
        """Test handling of empty agent input"""
        # Ensure no prompt is set
        runner._version.prompt = []

        # Create empty agent input
        agent_input = AgentInput()

        # Call _build_messages without mocking
        result = await runner._build_messages(agent_input)

        # Should return empty list
        assert result == []
