# ruff: noqa: S101

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from core.domain.models.models import Model
from core.domain.models.providers import Provider


class ProviderTestCase(ABC):
    @abstractmethod
    def provider(self) -> Provider:
        pass

    def __str__(self) -> str:
        return self.provider()

    @abstractmethod
    def model(self) -> Model:
        pass

    @abstractmethod
    def validate_structured_output_request(self, payload: dict[str, Any], request: httpx.Request):
        pass

    @abstractmethod
    def check_temperature(self, value: float, payload: dict[str, Any], request: httpx.Request):
        pass

    @abstractmethod
    def check_max_tokens(self, value: int, payload: dict[str, Any], request: httpx.Request):
        pass

    @abstractmethod
    def check_top_p(self, value: float, payload: dict[str, Any], request: httpx.Request):
        pass

    @abstractmethod
    def check_presence_penalty(self, value: float, payload: dict[str, Any], request: httpx.Request):
        pass

    @abstractmethod
    def check_frequency_penalty(self, value: float, payload: dict[str, Any], request: httpx.Request):
        pass

    @abstractmethod
    def check_parallel_tool_calls(self, value: bool, payload: dict[str, Any], request: httpx.Request):
        pass


class OpenAITestCase(ProviderTestCase):
    def provider(self) -> Provider:
        return Provider.OPEN_AI

    def model(self) -> Model:
        return Model.GPT_41_MINI_2025_04_14

    def validate_structured_output_request(self, payload: dict[str, Any], request: httpx.Request):
        response_format = payload.get("response_format")
        assert response_format
        assert response_format.get("type") == "json_schema"
        json_schema = response_format.get("json_schema")
        assert json_schema
        assert "name" in json_schema
        assert json_schema["schema"] == {
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
            "type": "object",
            "additionalProperties": False,
        }

    def check_temperature(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("temperature") == value

    def check_max_tokens(self, value: int, payload: dict[str, Any], request: httpx.Request):
        # max_tokens is deprecated
        assert payload.get("max_completion_tokens") == value

    def check_top_p(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("top_p") == value

    def check_presence_penalty(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("presence_penalty") == value

    def check_frequency_penalty(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("frequency_penalty") == value

    def check_parallel_tool_calls(self, value: bool, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("parallel_tool_calls") == value


class GroqTestCase(ProviderTestCase):
    def provider(self) -> Provider:
        return Provider.GROQ

    def model(self) -> Model:
        return Model.LLAMA_4_MAVERICK_FAST

    def validate_structured_output_request(self, payload: dict[str, Any], request: httpx.Request):
        # Groq does not support structured output very well
        # Instead the payload should be inlined in the message
        response_format = payload.get("response_format")
        assert response_format == {"type": "text"}

        messages = payload.get("messages")
        assert messages
        assert len(messages) == 2
        message = messages[0]
        assert message.get("role") == "system"
        content = message.get("content")
        assert "Return a single JSON object enforcing the following schema" in content
        # Extract the JSON schema
        splits = content.split("```")
        assert len(splits) == 3
        json_schema_str = splits[1]
        assert json_schema_str.startswith("json")
        json_schema = json.loads(json_schema_str.removeprefix("json"))
        assert json_schema

    def check_temperature(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("temperature") == value

    def check_max_tokens(self, value: int, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("max_tokens") == value

    def check_top_p(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("top_p") == value

    def check_presence_penalty(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("presence_penalty") == value

    def check_frequency_penalty(self, value: float, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("frequency_penalty") == value

    def check_parallel_tool_calls(self, value: bool, payload: dict[str, Any], request: httpx.Request):
        assert payload.get("parallel_tool_calls") == value
