from typing import Any, Literal, override

from pydantic import BaseModel

from core.domain.models import Model, Provider
from core.providers._base.utils import get_provider_config_env
from core.providers.openai.openai_provider_base import OpenAIProviderBase


class OpenAIConfig(BaseModel):
    provider: Literal[Provider.OPEN_AI] = Provider.OPEN_AI

    url: str = "https://api.openai.com/v1/chat/completions"
    api_key: str

    def __str__(self):
        return f"OpenAIConfig(url={self.url}, api_key={self.api_key[:4]}****)"


class OpenAIProvider(OpenAIProviderBase[OpenAIConfig]):
    @override
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
        }

    @override
    def _request_url(self, model: Model, stream: bool) -> str:
        return self._config.url

    @override
    @classmethod
    def required_env_vars(cls) -> list[str]:
        return ["OPENAI_API_KEY"]

    @override
    @classmethod
    def name(cls) -> Provider:
        return Provider.OPEN_AI

    @override
    @classmethod
    def _default_config(cls, index: int) -> OpenAIConfig:
        return OpenAIConfig(
            api_key=get_provider_config_env("OPENAI_API_KEY", index),
            url=get_provider_config_env("OPENAI_URL", index, "https://api.openai.com/v1/chat/completions"),
        )

    @override
    def default_model(self) -> Model:
        return Model.GPT_41_NANO_2025_04_14
