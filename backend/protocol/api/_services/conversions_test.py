# pyright: reportPrivateUsage=false
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest

from core.domain.exceptions import BadRequestError
from core.domain.inference_usage import CompletionUsage as DomainCompletionUsage
from core.domain.inference_usage import InferenceUsage as DomainInferenceUsage
from core.domain.inference_usage import TokenUsage as DomainTokenUsage
from core.domain.tool import HostedTool as DomainHostedTool
from core.domain.tool import Tool as DomainTool
from core.domain.trace import LLMTrace as DomainLLMTrace
from core.domain.trace import ToolTrace as DomainToolTrace
from core.utils.uuid import uuid7_generation_time
from protocol.api._api_models import (
    Annotation,
    Message,
    Tool,
    ToolCallRequest,
    ToolCallResult,
)
from protocol.api._services.conversions import (
    _extract_json_schema,
    annotation_to_domain,
    completion_from_domain,
    deployment_from_domain,
    experiments_url,
    graph_from_domain,
    graph_to_domain,
    message_to_domain,
    tool_to_domain,
    trace_from_domain,
    trace_to_domain,
    usage_from_domain,
    usage_to_domain,
    version_from_domain,
    version_to_domain,
    view_from_domain,
    view_to_domain,
    view_url,
)
from tests.fake_models import fake_completion, fake_deployment, fake_graph, fake_version, fake_view


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


class TestTraceConversion:
    def test_round_trip_conversion_llm_trace(self):
        """Test that LLM trace conversion is consistent in both directions."""
        original_domain = DomainLLMTrace(
            duration_seconds=2.0,
            cost_usd=0.02,
            model="test-model",
            provider="test-provider",
            usage=None,
        )

        # Convert to API and back
        api_trace = trace_from_domain(original_domain)
        converted_domain = trace_to_domain(api_trace)

        assert isinstance(converted_domain, DomainLLMTrace)
        assert converted_domain.duration_seconds == original_domain.duration_seconds
        assert converted_domain.cost_usd == original_domain.cost_usd
        assert converted_domain.model == original_domain.model
        assert converted_domain.provider == original_domain.provider
        assert converted_domain.usage == original_domain.usage

    def test_round_trip_conversion_tool_trace(self):
        """Test that tool trace conversion is consistent in both directions."""
        original_domain = DomainToolTrace(
            duration_seconds=1.5,
            cost_usd=0.005,
            name="test-tool",
            tool_input_preview='{"input": "test"}',
            tool_output_preview='{"output": "result"}',
        )

        # Convert to API and back
        api_trace = trace_from_domain(original_domain)
        converted_domain = trace_to_domain(api_trace)

        assert isinstance(converted_domain, DomainToolTrace)
        assert converted_domain.duration_seconds == original_domain.duration_seconds
        assert converted_domain.cost_usd == original_domain.cost_usd
        assert converted_domain.name == original_domain.name
        assert converted_domain.tool_input_preview == original_domain.tool_input_preview
        assert converted_domain.tool_output_preview == original_domain.tool_output_preview


class TestUsageConversion:
    def test_usage_round_trip_conversion(self):
        """Test that usage conversion is consistent in both directions."""
        original_domain = DomainInferenceUsage(
            prompt=DomainTokenUsage(
                text_token_count=100,
                audio_token_count=0,
                audio_count=0,
                image_token_count=10,
                image_count=1,
                cost_usd=0.02,
            ),
            completion=DomainCompletionUsage(
                text_token_count=40,
                cost_usd=0.008,
            ),
        )

        # Convert to API and back
        api_usage = usage_from_domain(original_domain)
        converted_domain = usage_to_domain(api_usage)

        assert converted_domain.prompt.text_token_count == original_domain.prompt.text_token_count
        assert converted_domain.prompt.audio_token_count == original_domain.prompt.audio_token_count
        assert converted_domain.prompt.audio_count == original_domain.prompt.audio_count
        assert converted_domain.prompt.image_token_count == original_domain.prompt.image_token_count
        assert converted_domain.prompt.image_count == original_domain.prompt.image_count
        assert converted_domain.prompt.cost_usd == original_domain.prompt.cost_usd
        assert converted_domain.completion.text_token_count == original_domain.completion.text_token_count
        assert converted_domain.completion.cost_usd == original_domain.completion.cost_usd


class TestCompletionConversion:
    def test_completion_from_domain_includes_created_at(self):
        """Test that completion_from_domain derives created_at from UUID7 ID."""

        # Create a fake completion with a UUID7 ID
        domain_completion = fake_completion(id_rand=12345)

        # Convert to API model
        api_completion = completion_from_domain(domain_completion)

        # Verify created_at is set and matches the UUID7 timestamp
        assert api_completion.created_at is not None
        expected_created_at = uuid7_generation_time(domain_completion.id)
        # Compare timestamps (allowing for microsecond sanitization)
        assert api_completion.created_at.replace(microsecond=0, tzinfo=UTC) == expected_created_at.replace(
            microsecond=0,
            tzinfo=UTC,
        )


class TestExtractJsonSchema:
    """Test the _extract_json_schema function."""

    def test_empty_dict_input(self):
        """Test that empty dict input returns None."""
        assert _extract_json_schema({}) is None

    def test_object_type(self):
        """Test that object type returns the schema as-is."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = _extract_json_schema(schema)
        assert result == schema

    def test_json_object_type(self):
        """Test that json_object type returns empty dict."""
        schema = {"type": "json_object"}
        result = _extract_json_schema(schema)
        assert result == {}

    def test_text_type(self):
        """Test that text type returns None."""
        schema = {"type": "text"}
        result = _extract_json_schema(schema)
        assert result is None

    def test_array_type_raises_error(self):
        """Test that array root type raises BadRequestError."""
        schema = {"type": "array", "items": {"type": "string"}}
        with pytest.raises(BadRequestError, match="Array as root types are not supported"):
            _extract_json_schema(schema)

    def test_string_type_raises_error(self):
        """Test that string root type raises BadRequestError."""
        schema = {"type": "string"}
        with pytest.raises(
            BadRequestError,
            match="String, integer, number, and boolean as root types are not supported",
        ):
            _extract_json_schema(schema)

    def test_integer_type_raises_error(self):
        """Test that integer root type raises BadRequestError."""
        schema = {"type": "integer"}
        with pytest.raises(
            BadRequestError,
            match="String, integer, number, and boolean as root types are not supported",
        ):
            _extract_json_schema(schema)

    def test_number_type_raises_error(self):
        """Test that number root type raises BadRequestError."""
        schema = {"type": "number"}
        with pytest.raises(
            BadRequestError,
            match="String, integer, number, and boolean as root types are not supported",
        ):
            _extract_json_schema(schema)

    def test_boolean_type_raises_error(self):
        """Test that boolean root type raises BadRequestError."""
        schema = {"type": "boolean"}
        with pytest.raises(
            BadRequestError,
            match="String, integer, number, and boolean as root types are not supported",
        ):
            _extract_json_schema(schema)

    def test_no_type_with_json_schema_key(self):
        """Test extraction when type is None but json_schema key exists."""
        inner_schema = {"type": "object", "properties": {"id": {"type": "string"}}}
        schema = {"json_schema": inner_schema}
        result = _extract_json_schema(schema)
        assert result == inner_schema

    def test_no_type_with_schema_key(self):
        """Test extraction when type is None but schema key exists."""
        inner_schema = {"type": "object", "properties": {"id": {"type": "number"}}}
        schema = {"schema": inner_schema}
        result = _extract_json_schema(schema)
        assert result == inner_schema

    def test_no_type_no_keys_raises_error(self):
        """Test that no type and no json_schema/schema keys raises BadRequestError."""
        schema = {"some_other_key": "value"}
        with pytest.raises(BadRequestError, match="Invalid output json schema"):
            _extract_json_schema(schema)

    def test_json_schema_type_with_valid_format(self):
        """Test json_schema type with valid OpenAI response format."""
        inner_schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        schema = {
            "type": "json_schema",
            "json_schema": {
                "schema": inner_schema,
                "name": "test_schema",
                "strict": True,
            },
        }
        # This will succeed because the format is actually valid
        result = _extract_json_schema(schema)
        assert result == inner_schema

    def test_json_schema_type_missing_json_schema(self):
        """Test json_schema type without json_schema field raises error."""
        schema = {"type": "json_schema"}
        with pytest.raises(BadRequestError, match="JSON Schema response format must have a json_schema"):
            _extract_json_schema(schema)

    def test_json_schema_type_invalid_format(self):
        """Test json_schema type with invalid format raises error."""
        schema = {
            "type": "json_schema",
            "json_schema": {"invalid_field": "value"},  # Invalid structure, no "schema" field
        }
        with pytest.raises(BadRequestError, match="Invalid JSON Schema response format"):
            _extract_json_schema(schema)

    def test_unknown_type_raises_error(self):
        """Test that unknown type raises BadRequestError."""
        schema = {"type": "unknown_type"}
        with pytest.raises(BadRequestError, match="Invalid output json schema"):
            _extract_json_schema(schema)

    def test_json_schema_type(self):
        inner_schema = {"type": "object", "properties": {"data": {"type": "string"}}}

        schema = {
            "type": "json_schema",
            "json_schema": {
                "schema": inner_schema,
            },
        }

        result = _extract_json_schema(schema)
        assert result == inner_schema

    def test_json_schema_type_without_schema_field(self):
        """Test json_schema type when validated object has no json_schema field."""

        schema = {"type": "json_schema"}

        with pytest.raises(BadRequestError, match="JSON Schema response format must have a json_schema"):
            _extract_json_schema(schema)

    def test_nested_json_schema_type(self):
        """Test json_schema type when validated object has a json_schema field."""
        schema = {"json_schema": {"type": "object", "properties": {"data": {"type": "string"}}}}
        result = _extract_json_schema(schema)
        assert result == {"type": "object", "properties": {"data": {"type": "string"}}}


def _annotation(**kwargs: Any) -> Annotation:
    ann = Annotation(
        id="test-annotation",
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC),
        author_name="Test Author",
    )
    return Annotation.model_validate(
        {
            **ann.model_dump(),
            **kwargs,
        },
    )


class TestAnnotationToDomainConversion:
    """Test the annotation_to_domain conversion function, especially ID sanitization."""

    def test_annotation_to_domain_basic(self):
        """Test basic annotation conversion without target or context."""

        api_annotation = _annotation()

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.id == "test-annotation"
        assert domain_annotation.target is None
        assert domain_annotation.context is None
        assert domain_annotation.metric is None

    def test_annotation_to_domain_with_metric(self):
        """Test annotation conversion with metric."""

        api_annotation = _annotation(
            metric=Annotation.Metric(name="accuracy", value=0.95),
        )

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.metric is not None
        assert domain_annotation.metric.name == "accuracy"
        assert domain_annotation.metric.value == 0.95

    @pytest.mark.parametrize(
        ("completion_id_input", "expected_uuid_str"),
        [
            # Plain UUID7 - should pass through sanitization
            ("01997d25-b859-7066-681c-c11fe1250b89", "01997d25-b859-7066-681c-c11fe1250b89"),
            # Prefixed with anotherai/completion/
            ("anotherai/completion/01997d25-b859-7066-681c-c11fe1250b89", "01997d25-b859-7066-681c-c11fe1250b89"),
            # Just prefixed with completion/
            ("completion/01997d25-b859-7066-681c-c11fe1250b89", "01997d25-b859-7066-681c-c11fe1250b89"),
        ],
    )
    def test_completion_id_sanitization_valid(self, completion_id_input, expected_uuid_str):
        """Test that valid completion IDs are properly sanitized."""

        api_annotation = _annotation(
            target=Annotation.Target(completion_id=completion_id_input),
        )

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.target is not None
        assert domain_annotation.target.completion_id == UUID(expected_uuid_str)

    @pytest.mark.parametrize(
        "completion_id_input",
        [
            # Invalid UUID format
            "invalid-uuid",
            # Wrong ID type prefix
            "anotherai/experiment/01997d25-b859-7066-681c-c11fe1250b89",
            # Non-UUID7 format (regular UUID4)
            "550e8400-e29b-41d4-a716-446655440000",
        ],
    )
    def test_completion_id_sanitization_invalid(self, completion_id_input: str):
        """Test that invalid completion IDs raise BadRequestError."""

        api_annotation = _annotation(
            target=Annotation.Target(completion_id=completion_id_input),
        )

        with pytest.raises(BadRequestError, match="Invalid completion id"):
            annotation_to_domain(api_annotation)

    def test_completion_id_none(self):
        """Test that None completion ID is properly sanitized."""

        api_annotation = _annotation(
            target=Annotation.Target(completion_id=None),
        )

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.target is not None
        assert domain_annotation.target.completion_id is None

    @pytest.mark.parametrize(
        ("experiment_id_input", "expected_id"),
        [
            # Plain experiment ID
            ("test-experiment-123", "test-experiment-123"),
            # Prefixed with anotherai/experiment/
            ("anotherai/experiment/test-experiment-123", "test-experiment-123"),
            # Just prefixed with experiment/
            ("experiment/test-experiment-123", "test-experiment-123"),
            # UUID7 format
            ("01997d25-b859-7066-681c-c11fe1250b89", "01997d25-b859-7066-681c-c11fe1250b89"),
            # Prefixed UUID7
            ("anotherai/experiment/01997d25-b859-7066-681c-c11fe1250b89", "01997d25-b859-7066-681c-c11fe1250b89"),
        ],
    )
    def test_experiment_id_sanitization_valid_target(self, experiment_id_input: str, expected_id: str):
        """Test that valid experiment IDs in target are properly sanitized."""

        api_annotation = _annotation(
            target=Annotation.Target(experiment_id=experiment_id_input),
        )

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.target is not None
        assert domain_annotation.target.experiment_id == expected_id

    @pytest.mark.parametrize(
        ("experiment_id_input", "expected_id"),
        [
            # Plain experiment ID
            ("test-experiment-456", "test-experiment-456"),
            # Prefixed with anotherai/experiment/
            ("anotherai/experiment/test-experiment-456", "test-experiment-456"),
            # Just prefixed with experiment/
            ("experiment/test-experiment-456", "test-experiment-456"),
        ],
    )
    def test_experiment_id_sanitization_valid_context(self, experiment_id_input: str, expected_id: str):
        """Test that valid experiment IDs in context are properly sanitized."""

        api_annotation = _annotation(
            context=Annotation.Context(experiment_id=experiment_id_input),
        )

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.context is not None
        assert domain_annotation.context.experiment_id == expected_id

    @pytest.mark.parametrize(
        "experiment_id_input",
        [
            # Wrong ID type prefix
            "anotherai/completion/01997d25-b859-7066-681c-c11fe1250b89",
            "anotherai/agent/test-agent",
        ],
    )
    def test_experiment_id_sanitization_invalid(self, experiment_id_input: str):
        """Test that invalid experiment IDs raise BadRequestError."""

        api_annotation = _annotation(
            target=Annotation.Target(experiment_id=experiment_id_input),
        )

        with pytest.raises(BadRequestError, match="Invalid experiment id"):
            annotation_to_domain(api_annotation)

    @pytest.mark.parametrize(
        ("agent_id_input", "expected_id"),
        [
            # Plain agent ID
            ("test-agent", "test-agent"),
            # Prefixed with anotherai/agent/
            ("anotherai/agent/test-agent", "test-agent"),
            # Just prefixed with agent/
            ("agent/test-agent", "test-agent"),
            # Agent with special characters
            ("my-test-agent_123", "my-test-agent_123"),
        ],
    )
    def test_agent_id_sanitization_valid(self, agent_id_input: str, expected_id: str):
        """Test that valid agent IDs are properly sanitized."""

        api_annotation = _annotation(
            context=Annotation.Context(agent_id=agent_id_input),
        )

        domain_annotation = annotation_to_domain(api_annotation)

        assert domain_annotation.context is not None
        assert domain_annotation.context.agent_id == expected_id


class TestDeploymentFromDomain:
    def test_deployment_from_domain(self):
        domain_deployment = fake_deployment()
        converted = deployment_from_domain(domain_deployment)
        assert converted.id == "anotherai/deployment/test-deployment"
