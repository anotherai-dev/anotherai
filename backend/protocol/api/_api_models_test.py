import pytest
from pydantic import ValidationError

from protocol.api._api_models import ToolCallResult, Version


class TestVersion:
    def test_minimal_payload(self):
        only_model = Version.model_validate(
            {
                "model": "gpt-4o",
            },
        )
        assert only_model.model == "gpt-4o"


class TestToolCallResult:
    def test_minimal_payload(self):
        tool_call_result = ToolCallResult.model_validate(
            {
                "id": "hello",
                "output": "world",
            },
        )
        assert tool_call_result.id == "hello"
        assert tool_call_result.output == "world"
        assert tool_call_result.error is None

    def test_error_payload(self):
        tool_call_result = ToolCallResult.model_validate(
            {
                "id": "hello",
                "error": "world",
            },
        )
        assert tool_call_result.id == "hello"
        assert tool_call_result.error == "world"
        assert tool_call_result.output is None

    def test_empty_payload(self):
        with pytest.raises(ValidationError):
            ToolCallResult.model_validate({"id": "hello"})
