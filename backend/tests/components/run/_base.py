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
