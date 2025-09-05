from unittest.mock import patch

import pytest

from core.domain.exceptions import BadRequestError
from core.domain.tool import HostedTool as DomainHostedTool
from core.domain.tool import Tool as DomainTool
from protocol.api._api_models import Message, Tool, ToolCallRequest, ToolCallResult
from protocol.api._services.conversions import (
    experiments_url,
    graph_from_domain,
    graph_to_domain,
    message_to_domain,
    tool_to_domain,
    version_from_domain,
    version_to_domain,
    view_from_domain,
    view_to_domain,
    view_url,
)
from tests.fake_models import fake_graph, fake_version, fake_view


@pytest.fixture(autouse=True)
def patched_app_url():
    base = "https://anotherai.dev"
    with patch("protocol.api._services._urls.ANOTHERAI_APP_URL", new=base):
        yield base


def test_experiments_url(patched_app_url: str):
    assert experiments_url("123") == f"{patched_app_url}/experiments/123"


def test_view_url(patched_app_url: str):
    assert view_url(view_id="456") == f"{patched_app_url}/views/456"


class TestViewConversion:
    def test_exhaustive(self, patched_app_url: str):
        domain_view = fake_view()
        converted = view_from_domain(domain_view)
        # Check all fields are set
        assert converted.model_dump(exclude_unset=True, exclude_none=True) == converted.model_dump(
            exclude_none=True,
        ), "dashboard_view_from_domain is not exhaustive"

        domain_converted = view_to_domain(converted)
        assert domain_converted.model_dump(exclude_unset=True, exclude_none=True) == domain_converted.model_dump(
            exclude_none=True,
        ), "view_to_domain is not exhaustive"
        # Fields are not present in the API model
        domain_converted.position = domain_view.position
        domain_converted.folder_id = domain_view.folder_id
        assert domain_converted == domain_view


class TestGraphConversion:
    def test_exhaustive(self, patched_app_url: str):
        domain_graph = fake_graph()
        converted = graph_from_domain(domain_graph)
        assert converted is not None, "graph_from_domain returned None"
        assert converted.model_dump(exclude_unset=True, exclude_none=True) == converted.model_dump(
            exclude_none=True,
        ), "graph_from_domain is not exhaustive"

        domain_converted = graph_to_domain(converted)
        assert domain_converted.model_dump(exclude_unset=True, exclude_none=True) == domain_converted.model_dump(
            exclude_none=True,
        ), "graph_to_domain is not exhaustive"


class TestMessageToDomain:
    """Test the message_to_domain conversion function."""

    def test_role_conversion_system(self):
        """Test that system role is converted correctly."""
        message = Message(role="system", content="Hello")
        domain_message = message_to_domain(message)
        assert domain_message.role == "system"

    def test_role_conversion_developer(self):
        """Test that developer role is converted to system."""
        message = Message(role="developer", content="Hello")
        domain_message = message_to_domain(message)
        assert domain_message.role == "system"

    def test_role_conversion_user(self):
        """Test that user role is converted correctly."""
        message = Message(role="user", content="Hello")
        domain_message = message_to_domain(message)
        assert domain_message.role == "user"

    def test_role_conversion_tool(self):
        """Test that tool role is converted to user."""
        message = Message(role="tool", content="Hello")
        domain_message = message_to_domain(message)
        assert domain_message.role == "user"

    def test_role_conversion_assistant(self):
        """Test that assistant role is converted correctly."""
        message = Message(role="assistant", content="Hello")
        domain_message = message_to_domain(message)
        assert domain_message.role == "assistant"

    def test_content_string_simple(self):
        """Test conversion of simple string content."""
        message = Message(role="user", content="Hello world")
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].text == "Hello world"
        assert domain_message.content[0].object is None

    def test_content_dict_object(self):
        """Test conversion of dict content to object."""
        test_object = {"key": "value", "number": 42}
        message = Message(role="user", content=test_object)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].object == test_object
        assert domain_message.content[0].text is None

    def test_content_list_with_text(self):
        """Test conversion of list content with text."""
        content = [Message.Content(text="Hello world")]
        message = Message(role="user", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].text == "Hello world"

    def test_content_list_with_image_url(self):
        """Test conversion of list content with image URL."""
        image_url = "https://example.com/image.jpg"
        content = [Message.Content(image_url=image_url)]
        message = Message(role="user", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].file is not None
        assert domain_message.content[0].file.url == image_url
        assert domain_message.content[0].file.format == "image"

    def test_content_list_with_audio_url(self):
        """Test conversion of list content with audio URL."""
        audio_url = "https://example.com/audio.mp3"
        content = [Message.Content(audio_url=audio_url)]
        message = Message(role="user", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].file is not None
        assert domain_message.content[0].file.url == audio_url
        assert domain_message.content[0].file.format == "audio"

    def test_content_list_with_tool_call_request(self):
        """Test conversion of list content with tool call request."""
        tool_call = ToolCallRequest(
            id="call_123",
            name="test_tool",
            arguments={"param": "value"},
        )
        content = [Message.Content(tool_call_request=tool_call)]
        message = Message(role="assistant", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].tool_call_request is not None
        assert domain_message.content[0].tool_call_request.id == "call_123"
        assert domain_message.content[0].tool_call_request.tool_name == "test_tool"
        assert domain_message.content[0].tool_call_request.tool_input_dict == {"param": "value"}

    def test_content_list_with_tool_call_result(self):
        """Test conversion of list content with tool call result."""
        tool_result = ToolCallResult(
            id="call_123",
            output="Tool executed successfully",
            error=None,
        )
        content = [Message.Content(tool_call_result=tool_result)]
        message = Message(role="tool", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].tool_call_result is not None
        assert domain_message.content[0].tool_call_result.id == "call_123"
        assert domain_message.content[0].tool_call_result.result == "Tool executed successfully"
        assert domain_message.content[0].tool_call_result.error is None

    def test_content_list_with_tool_call_result_error(self):
        """Test conversion of list content with tool call result that has an error."""
        tool_result = ToolCallResult(
            id="call_123",
            output=None,
            error="Tool execution failed",
        )
        content = [Message.Content(tool_call_result=tool_result)]
        message = Message(role="tool", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].tool_call_result is not None
        assert domain_message.content[0].tool_call_result.id == "call_123"
        assert domain_message.content[0].tool_call_result.result is None
        assert domain_message.content[0].tool_call_result.error == "Tool execution failed"

    def test_content_multiple_fields_error(self):
        """Test that having multiple fields in content raises BadRequestError."""
        # This should raise an error because both text and image_url are set
        content = [Message.Content(text="Hello", image_url="https://example.com/image.jpg")]
        message = Message(role="user", content=content)

        with pytest.raises(BadRequestError, match="Contents can only contain one field at a time"):
            message_to_domain(message)

    def test_content_empty_content(self):
        """Test conversion with empty content list."""
        content = []
        message = Message(role="user", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 0

    @pytest.mark.parametrize(
        ("role", "expected_domain_role"),
        [
            ("system", "system"),
            ("developer", "system"),
            ("user", "user"),
            ("tool", "user"),
            ("assistant", "assistant"),
        ],
    )
    def test_all_role_mappings(self, role, expected_domain_role):
        """Parametrized test for all role mappings."""
        message = Message(role=role, content="test")
        domain_message = message_to_domain(message)
        assert domain_message.role == expected_domain_role

    def test_content_with_only_reasoning(self):
        """Test content that has only reasoning field set."""
        content = [Message.Content(reasoning="Just reasoning, no text")]
        message = Message(role="assistant", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].text is None
        assert domain_message.content[0].reasoning == "Just reasoning, no text"

    def test_content_list_with_object(self):
        """Test conversion of list content with object field."""
        test_object = {"type": "custom", "data": {"key": "value", "number": 42}}
        content = [Message.Content(object=test_object)]
        message = Message(role="user", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].object == test_object
        assert domain_message.content[0].text is None
        assert domain_message.content[0].file is None
        assert domain_message.content[0].tool_call_request is None
        assert domain_message.content[0].tool_call_result is None

    def test_content_none_values(self):
        """Test content with all None values."""
        content = [Message.Content()]  # All fields are None by default
        message = Message(role="user", content=content)
        domain_message = message_to_domain(message)

        assert len(domain_message.content) == 1
        assert domain_message.content[0].text is None
        assert domain_message.content[0].object is None
        assert domain_message.content[0].file is None
        assert domain_message.content[0].tool_call_request is None
        assert domain_message.content[0].tool_call_result is None
        assert domain_message.content[0].reasoning is None


class TestVersionConversion:
    def test_exhaustive(self):
        domain_version = fake_version()
        converted = version_from_domain(domain_version)
        assert converted.model_fields_set == set(converted.__class__.model_fields), (
            "version_from_domain is not exhaustive"
        )

        domain_converted = version_to_domain(converted)
        assert domain_converted.model_fields_set == set(domain_converted.__class__.model_fields), (
            "version_to_domain is not exhaustive"
        )

        assert domain_converted.model_dump(exclude_unset=True, exclude_none=True) == domain_version.model_dump(
            exclude_unset=True,
            exclude_none=True,
        ), "version_from_domain and version_to_domain are not inverses"


class TestToolConversion:
    def test_hosted_tool(self):
        tool = Tool(name="@browser-text", input_schema={})
        domain_tool = tool_to_domain(tool)
        assert domain_tool == DomainHostedTool.WEB_BROWSER_TEXT

    def test_tool(self):
        tool = Tool(name="test", input_schema={})
        domain_tool = tool_to_domain(tool)
        assert domain_tool == DomainTool(name="test", input_schema={})
