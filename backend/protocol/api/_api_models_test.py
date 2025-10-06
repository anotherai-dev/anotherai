import pytest
from pydantic import ValidationError

from core.domain.reasoning_effort import ReasoningEffort
from protocol.api._api_models import Model, ModelField, ToolCallResult, Version


class TestVersion:
    def test_minimal_payload(self):
        only_model = Version.model_validate(
            {
                "model": "gpt-4o",
            },
        )
        assert only_model.model == "gpt-4o"

    def test_reasoning_effort(self):
        version = Version.model_validate(
            {
                "model": "gpt-4o",
                "reasoning_effort": "disabled",
            },
        )
        assert version.reasoning_effort == ReasoningEffort.DISABLED


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


class TestModelFields:
    def test_subset_of_model(self):
        for m in ModelField:
            assert m.value in Model.model_fields, f"{m.value} not in {Model.model_fields}"
