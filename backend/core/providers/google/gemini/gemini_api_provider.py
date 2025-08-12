from typing import Any, Literal, override

from pydantic import BaseModel

from core.domain.file import File
from core.domain.models import Model, Provider
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.utils import get_provider_config_env
from core.providers.google.google_provider_base import GoogleProviderBase
from core.providers.google.google_provider_domain import (
    BLOCK_THRESHOLD,
    message_or_system_message,
)


class GoogleGeminiAPIProviderConfig(BaseModel):
    provider: Literal[Provider.GOOGLE_GEMINI] = Provider.GOOGLE_GEMINI
    api_key: str
    url: str = "https://generativelanguage.googleapis.com"

    default_block_threshold: BLOCK_THRESHOLD | None = None

    def __str__(self):
        return f"GeminiAPIProviderConfig(url={self.url}, api_key={self.api_key[:4]}****)"


class GoogleGeminiAPIProvider(GoogleProviderBase[GoogleGeminiAPIProviderConfig]):
    model_api_versions: dict[Model, str] = {
        Model.GEMINI_2_0_FLASH_THINKING_EXP_1219: "v1alpha",
        Model.GEMINI_2_0_FLASH_THINKING_EXP_0121: "v1alpha",
    }

    @override
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
        }

    @override
    def _request_url(self, model: Model, stream: bool) -> str:
        if stream:
            suffix = f"streamGenerateContent?alt=sse&key={self._config.api_key}"
        else:
            suffix = f"generateContent?key={self._config.api_key}"

        model_str = self._model_url_str(model)
        api_version = self.model_api_versions.get(model, "v1beta")
        return f"{self._config.url}/{api_version}/models/{model_str}:{suffix}"

    @override
    @classmethod
    def required_env_vars(cls) -> list[str]:
        return ["GEMINI_API_KEY"]

    @override
    @classmethod
    def name(cls) -> Provider:
        return Provider.GOOGLE_GEMINI

    @override
    @classmethod
    def _default_config(cls, index: int) -> GoogleGeminiAPIProviderConfig:
        return GoogleGeminiAPIProviderConfig(
            api_key=get_provider_config_env("GEMINI_API_KEY", index),
        )

    def _compute_prompt_token_count_per_token(self, messages: list[dict[str, Any]], model: Model) -> float:
        token_count = 0

        for message in messages:
            domain_message = message_or_system_message(message)

            message_token_count = domain_message.text_token_count(model)
            token_count += message_token_count

        return token_count

    @property
    def response_schema_allowed_string_formats(self) -> set[str] | None:
        # Gemini API does not support all string formats in the response schemas
        # see https://ai.google.dev/api/caching?hl=fr#Schema
        return {"enum", "date-time"}

    @override
    def _compute_prompt_token_count(
        self,
        messages: list[dict[str, Any]],
        model: Model,
    ) -> float:
        return self._compute_prompt_token_count_per_token(messages, model)

    @override
    async def feed_prompt_token_count(self, llm_usage: LLMUsage, messages: list[dict[str, Any]], model: Model) -> None:
        if llm_usage.prompt_token_count is None:
            llm_usage.prompt_token_count = self._compute_prompt_token_count(messages, model)
            if llm_usage.prompt_audio_token_count is not None:
                llm_usage.prompt_token_count += llm_usage.prompt_audio_token_count

    @override
    @classmethod
    def requires_downloading_file(cls, file: File, model: Model) -> bool:
        # Gemini API requires downloading files, as the URL is not GCP URL
        return True
