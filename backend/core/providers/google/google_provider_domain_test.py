import base64
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from core.domain.exceptions import InvalidRunOptionsError
from core.domain.message import File, MessageDeprecated
from core.domain.models import Model
from core.domain.tool import Tool
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.providers.google.google_provider_domain import (
    Blob,
    CompletionResponse,
    GoogleMessage,
    GoogleSystemMessage,
    Part,
    Schema,
    internal_tool_name_to_native_tool_call,
    native_tool_name_to_internal,
)
from core.providers.google.google_provider_domain import (
    Schema as GoogleSchema,
)
from core.utils.schemas import JsonSchema
from tests.utils import fixture_bytes


class TestGoogleMessageFromDomain:
    def test_with_text(self):
        # Test with text content
        text_message = MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello, world!")
        google_message = GoogleMessage.from_domain(text_message)
        assert len(google_message.parts) == 1
        assert google_message.parts[0].text == "Hello, world!"
        assert google_message.role == "user"

        # Test with image content
        image_data = base64.b64encode(b"fake_image_data").decode()
        image_message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Check this image:",
            files=[File(data=image_data, content_type="image/png")],
        )
        google_message = GoogleMessage.from_domain(image_message)
        assert len(google_message.parts) == 2
        assert google_message.parts[0].text == "Check this image:"
        assert google_message.parts[1].inlineData
        assert google_message.parts[1].inlineData.mimeType == "image/png"
        assert google_message.parts[1].inlineData.data == image_data
        assert google_message.role == "user"

        # Test assistant message
        assistant_message = MessageDeprecated(role=MessageDeprecated.Role.ASSISTANT, content="I'm here to help!")
        google_message = GoogleMessage.from_domain(assistant_message)
        assert len(google_message.parts) == 1
        assert google_message.parts[0].text == "I'm here to help!"
        assert google_message.role == "model"

    def test_file_url(self):
        text_message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Hello, world!",
            files=[File(url="https://example.com/image.png", content_type="image/png")],
        )
        google_message = GoogleMessage.from_domain(text_message)
        assert len(google_message.parts) == 2
        assert google_message.parts[0].text == "Hello, world!"
        assert google_message.parts[1].fileData
        assert google_message.parts[1].fileData.fileUri == "https://example.com/image.png"
        assert google_message.parts[1].fileData.mimeType == "image/png"
        assert google_message.role == "user"

    def test_empty_content(self):
        image_only_message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="",
            files=[File(url="https://example.com/image.png", content_type="image/png")],
        )
        google_message = GoogleMessage.from_domain(image_only_message)
        assert len(google_message.parts) == 2
        assert google_message.parts[0].text == "-"
        assert google_message.parts[1].fileData
        assert google_message.parts[1].fileData.fileUri == "https://example.com/image.png"
        assert google_message.parts[1].fileData.mimeType == "image/png"
        assert google_message.role == "user"

    @pytest.mark.ffmpeg
    async def test_with_file_audio(self):
        # Test with text content
        text_message = MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello, world!")
        google_message = GoogleMessage.from_domain(text_message)
        assert len(google_message.parts) == 1
        assert google_message.parts[0].text == "Hello, world!"
        assert google_message.role == "user"

        # Test with audio data
        audio_data = base64.b64encode(fixture_bytes("files", "sample.mp3")).decode()

        audio_message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Check this audio:",
            files=[File(data=audio_data, content_type="audio/mpeg")],
        )
        google_message = GoogleMessage.from_domain(audio_message)
        assert len(google_message.parts) == 2
        assert google_message.parts[0].text == "Check this audio:"
        assert google_message.parts[1].inlineData
        assert google_message.parts[1].inlineData.mimeType == "audio/mpeg"
        assert google_message.parts[1].inlineData.data == audio_data
        assert google_message.role == "user"

        assert google_message.text_token_count(Model.GEMINI_1_5_FLASH_001) == 4
        assert await google_message.audio_duration_seconds() == 10.043

        # Test assistant message
        assistant_message = MessageDeprecated(role=MessageDeprecated.Role.ASSISTANT, content="I'm here to help!")
        google_message = GoogleMessage.from_domain(assistant_message)
        assert len(google_message.parts) == 1
        assert google_message.parts[0].text == "I'm here to help!"
        assert google_message.role == "model"

    def test_tool_calls_native(self):
        """Test GoogleMessage.from_domain with tool calls using native tools."""
        from core.domain.tool_call import ToolCallRequest

        dummy_req = ToolCallRequest(tool_name="@echo", tool_input_dict={"msg": "Hello from native tool"})
        dummy_res = ToolCallResult(
            tool_name="@echo",
            tool_input_dict={"msg": "Hello from native tool"},
            result="Native tool execution successful",
        )
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="Run native tool call:",
            tool_call_requests=[dummy_req],
            tool_call_results=[dummy_res],
        )
        google_message = GoogleMessage.from_domain(message)
        # Expected: parts: [text, tool call request, tool call result]
        assert len(google_message.parts) == 3
        # First part is the text
        assert google_message.parts[0].text == "Run native tool call:"
        # Second part is tool call request, check functionCall exists
        assert google_message.parts[1].functionCall is not None
        expected_name = dummy_req.tool_name.replace("@", "")
        assert google_message.parts[1].functionCall.name == expected_name
        assert google_message.parts[1].functionCall.args == {"msg": "Hello from native tool"}
        # Third part is tool call result, check functionResponse exists
        assert google_message.parts[2].functionResponse is not None
        expected_result_name = dummy_res.tool_name.replace("@", "")
        assert google_message.parts[2].functionResponse.name == expected_result_name
        assert google_message.parts[2].functionResponse.response == {"result": str(dummy_res.result)}

    def test_tool_call_no_content(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.USER,
            content="",
            tool_call_requests=[
                ToolCallRequest(tool_name="@echo", tool_input_dict={"msg": "Hello from native tool"}),
            ],
        )
        google_message = GoogleMessage.from_domain(message)
        assert len(google_message.parts) == 1

        assert google_message.parts[0].functionCall

    def test_tool_call_result_no_content(self):
        message = MessageDeprecated(
            role=MessageDeprecated.Role.ASSISTANT,
            content="",
            tool_call_results=[ToolCallResult(tool_name="@echo", tool_input_dict={"msg": "Hello from native tool"})],
        )
        google_message = GoogleMessage.from_domain(message)
        assert len(google_message.parts) == 1

        assert google_message.parts[0].functionResponse


def test_googlesystemmessage_from_domain_file():
    # Test valid system message
    system_message = MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="You are a helpful assistant.")
    anthropic_system_message = GoogleSystemMessage.from_domain(system_message)
    assert anthropic_system_message.parts[0].text == "You are a helpful assistant."

    # Test system message with image (should raise an error)
    image_data = base64.b64encode(b"fake_image_data").decode()
    system_message_with_image = MessageDeprecated(
        role=MessageDeprecated.Role.SYSTEM,
        content="System message with image",
        files=[File(data=image_data, content_type="image/png")],
    )
    with pytest.raises(InvalidRunOptionsError):
        GoogleSystemMessage.from_domain(system_message_with_image)


class TestBlobToURL:
    def test_blob_to_url(self):
        file = File(data=base64.b64encode(b"fake_image_data").decode(), content_type="image/png")
        blob = Blob.from_domain(file)
        assert file.to_url() == "data:image/png;base64,ZmFrZV9pbWFnZV9kYXRh", "sanity check"
        assert blob.to_url() == file.to_url()


class TestImageCount:
    def test_image_count_none(self):
        message = GoogleMessage(role="user", parts=[Part(text="Hello " * 102396)])
        assert message.image_count() == 0

    def test_image_count(self):
        message = GoogleMessage(
            role="user",
            parts=[
                Part(text="Hello " * 102396),
                Part(inlineData=Blob(mimeType="image/png", data="data")),
                Part(inlineData=Blob(mimeType="image/png", data="data1")),
            ],
        )
        assert message.image_count() == 2

    def test_image_count_with_other_files(self):
        message = GoogleMessage(
            role="user",
            parts=[
                Part(text="Hello " * 102396),
                Part(inlineData=Blob(mimeType="audio/mpeg", data="data")),
                Part(inlineData=Blob(mimeType="image/png", data="data1")),
            ],
        )
        assert message.image_count() == 1


def get_current_date() -> str:
    """Return today's date in ISO format (YYYY-MM-DD)"""
    return datetime.now(tz=ZoneInfo("UTC")).date().isoformat()


def calculate_days_between(date1: str, date2: str) -> int:
    """Calculate the number of days between two dates in ISO format (YYYY-MM-DD)"""
    d1 = date.fromisoformat(date1)
    d2 = date.fromisoformat(date2)
    return abs((d2 - d1).days)


# TODO: fix
@pytest.mark.skip(reason="TODO")
class TestSchemaFromJSONSchema:
    def test_schema_from_json_schema(self):
        tool = Tool(
            name="search_google",
            input_schema={},
            output_schema={},
        )
        google_schema = GoogleSchema.from_json_schema(JsonSchema(tool.input_schema))
        assert google_schema.model_dump(exclude_none=True) == Schema(
            type="OBJECT",
            format=None,
            description=None,
            nullable=False,
            enum=None,
            maxItems=None,
            minItems=None,
            properties={
                "query": Schema(
                    type="STRING",
                    format=None,
                    description=None,
                    nullable=False,
                    enum=None,
                    maxItems=None,
                    minItems=None,
                    properties=None,
                    required=None,
                    propertyOrdering=None,
                    items=None,
                ),
            },
            required=["query"],
            propertyOrdering=None,
            items=None,
        ).model_dump(exclude_none=True)

    def test_schema_from_json_schema_get_current_date(self):
        tool = Tool(
            name="get_current_date",
            input_schema={},
            output_schema={},
        )
        assert GoogleSchema.from_json_schema(JsonSchema(tool.input_schema)) == Schema(
            type="OBJECT",
            format=None,
            description=None,
            nullable=False,
            enum=None,
            maxItems=None,
            minItems=None,
            properties={},
            required=[],
            propertyOrdering=None,
            items=None,
        )
        assert tool.output_schema
        assert GoogleSchema.from_json_schema(JsonSchema(tool.output_schema)) == Schema(
            type="STRING",
            format=None,
            description=None,
            nullable=False,
            enum=None,
            maxItems=None,
            minItems=None,
            properties=None,
            required=None,
            propertyOrdering=None,
            items=None,
        )

    def test_schema_from_json_schema_calculate_days_between(self):
        tool = Tool(
            name="calculate_days_between",
            input_schema={},
            output_schema={},
        )
        assert GoogleSchema.from_json_schema(JsonSchema(tool.input_schema)) == Schema(
            type="OBJECT",
            format=None,
            description=None,
            nullable=False,
            enum=None,
            maxItems=None,
            minItems=None,
            properties={
                "date1": Schema(
                    type="STRING",
                    format=None,
                    description=None,
                    nullable=False,
                    enum=None,
                    maxItems=None,
                    minItems=None,
                    properties=None,
                    required=None,
                    propertyOrdering=None,
                    items=None,
                ),
                "date2": Schema(
                    type="STRING",
                    format=None,
                    description=None,
                    nullable=False,
                    enum=None,
                    maxItems=None,
                    minItems=None,
                    properties=None,
                    required=None,
                    propertyOrdering=None,
                    items=None,
                ),
            },
            required=["date1", "date2"],
            propertyOrdering=None,
            items=None,
        )
        assert tool.output_schema
        assert GoogleSchema.from_json_schema(JsonSchema(tool.output_schema)) == Schema(
            type="NUMBER",
            format=None,
            description=None,
            nullable=False,
            enum=None,
            maxItems=None,
            minItems=None,
            properties=None,
            required=None,
            propertyOrdering=None,
            items=None,
        )


def test_tool_name_to_google_tool_name():
    """Test conversion from internal tool names to Google tool names."""
    assert internal_tool_name_to_native_tool_call("@search-google") == "search-google"
    assert internal_tool_name_to_native_tool_call("@browser-text") == "browser-text"
    assert internal_tool_name_to_native_tool_call("no-at-symbol") == "no-at-symbol"
    assert internal_tool_name_to_native_tool_call("") == ""


def test_google_tool_name_to_tool_name():
    """Test conversion from Google tool names to internal tool names."""
    # Test with known tool kinds
    assert native_tool_name_to_internal("@search-google") == "@search-google"
    assert native_tool_name_to_internal("@browser-text") == "@browser-text"
    assert native_tool_name_to_internal("search-google") == "@search-google"
    assert native_tool_name_to_internal("browser-text") == "@browser-text"

    # Test with unknown tool names (should return as-is)
    assert native_tool_name_to_internal("unknown-tool") == "unknown-tool"
    assert native_tool_name_to_internal("") == ""


class TestPartFromToolCallResult:
    def test_from_tool_call_result_json_success(self):
        """Test Part.from_tool_call_result with valid JSON result."""

        tool_call_result = ToolCallResult(
            tool_name="@test_tool",
            tool_input_dict={"input": "test"},
            result='{"key": "value", "number": 42}',
        )

        part = Part.from_tool_call_result(tool_call_result)

        assert part.functionResponse is not None
        assert part.functionResponse.name == "test_tool"  # @ is removed
        assert part.functionResponse.response == {"key": "value", "number": 42}

    def test_from_tool_call_result_json_decode_error(self):
        """Test Part.from_tool_call_result with non-JSON result."""

        tool_call_result = ToolCallResult(
            tool_name="@test_tool",
            tool_input_dict={"input": "test"},
            result="This is not JSON",
        )

        part = Part.from_tool_call_result(tool_call_result)

        assert part.functionResponse is not None
        assert part.functionResponse.name == "test_tool"  # @ is removed
        assert part.functionResponse.response == {"result": "This is not JSON"}

    def test_from_tool_call_result_int(self):
        """Test Part.from_tool_call_result with non-JSON result."""

        tool_call_result = ToolCallResult(
            tool_name="@test_tool",
            tool_input_dict={"input": "test"},
            result="123",
        )

        part = Part.from_tool_call_result(tool_call_result)

        assert part.functionResponse is not None
        assert part.functionResponse.name == "test_tool"  # @ is removed
        assert part.functionResponse.response == {"result": "123"}


class TestCompletionResponseValidate:
    def test_validate_completion_response_no_candidates(self):
        payload = {
            "modelVersion": "gemini-2.0-flash-thinking-exp-01-21",
            "promptFeedback": {
                "blockReason": "OTHER",
            },
            "usageMetadata": {
                "promptTokenCount": 100,
                "totalTokenCount": 200,
            },
        }
        assert CompletionResponse.model_validate(payload)

    def test_empty_content(self):
        """Sometimes google returns a content: {}"""
        payload = {
            "candidates": [
                {
                    "citationMetadata": {
                        "citations": "[{'startIndex': 6249, 'endIndex': 18044, 'uri': 'https://www.scribd.com/document/73318603/Business-Chapter-06'}]",
                    },
                    "content": {},
                    "finishReason": "RECITATION",
                    "safetyRatings": [
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "probability": "NEGLIGIBLE",
                            "probabilityScore": 4.223497e-05,
                            "severity": "HARM_SEVERITY_NEGLIGIBLE",
                            "severityScore": 0.0984422,
                        },
                    ],
                },
            ],
        }
        assert CompletionResponse.model_validate(payload)
