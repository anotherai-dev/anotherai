from collections.abc import Iterable
from typing import Any, override

import structlog

from core.domain.exceptions import (
    MissingEnvVariablesError,
)
from core.domain.models import Provider
from core.domain.tenant_data import ProviderConfig
from core.providers._base.abstract_provider import AbstractProvider
from core.providers.amazon_bedrock.amazon_bedrock_provider import AmazonBedrockProvider
from core.providers.anthropic.anthropic_provider import AnthropicProvider
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.providers.fireworks.fireworks_provider import FireworksAIProvider
from core.providers.google.gemini.gemini_api_provider import GoogleGeminiAPIProvider
from core.providers.google.google_provider import GoogleProvider
from core.providers.groq.groq_provider import GroqProvider
from core.providers.mistral.mistral_provider import MistralAIProvider
from core.providers.openai.azure_open_ai_provider.azure_openai_provider import AzureOpenAIProvider
from core.providers.openai.openai_provider import OpenAIProvider
from core.providers.xai.xai_provider import XAIProvider

_provider_cls: list[type[AbstractProvider[Any, Any]]] = [
    OpenAIProvider,
    AzureOpenAIProvider,
    GroqProvider,
    GoogleProvider,
    AmazonBedrockProvider,
    MistralAIProvider,
    AnthropicProvider,
    GoogleGeminiAPIProvider,
    FireworksAIProvider,
    XAIProvider,
]

_log = structlog.get_logger("LocalProviderFactory")


class LocalProviderFactory(AbstractProviderFactory):
    """A provider factory that uses locally defined providers.
    To add a supported provider, add it to the PROVIDER_TYPES list."""

    # This should not be a class variable
    PROVIDER_TYPES: dict[Provider, type[AbstractProvider[Any, Any]]] = {
        provider.name(): provider for provider in _provider_cls
    }

    def __init__(self) -> None:
        self._providers = self.build_available_providers()

    @override
    def get_provider(self, provider: Provider, index: int = 0) -> AbstractProvider[Any, Any]:
        return self._providers[provider][index]

    @override
    def get_providers(self, provider: Provider) -> Iterable[AbstractProvider[Any, Any]]:
        # We return the providers in the order they were inserted
        # If prepare_all_providers was called first, it should be the same order
        return self._providers[provider]

    @classmethod
    def _build_providers_for_type(cls, provider: Provider):
        providers: list[AbstractProvider[Any, Any]] = []
        try:
            provider_type = cls.PROVIDER_TYPES[provider]
        except KeyError:
            raise ValueError(f"Provider {provider} not supported") from None

        for i in range(10):
            try:
                providers.append(provider_type(index=i))
                _log.info(
                    "Successfully prepared provider",
                    provider=provider,
                    index=i,
                )
            except MissingEnvVariablesError:
                if i == 0:
                    _log.warning(
                        "Skipping provider since env variables are missing",
                        provider=provider,
                        index=i,
                        missing_env_vars=provider_type.required_env_vars(),
                    )
                # We end at the first missing env variable
                break
            except Exception as e:  # noqa: BLE001
                _log.exception(
                    "Failed to prepare provider",
                    provider=provider,
                    index=i,
                    exc_info=e,
                )
        return providers

    @classmethod
    def build_available_providers(cls) -> dict[Provider, list[AbstractProvider[Any, Any]]]:
        return {provider: cls._build_providers_for_type(provider) for provider in LocalProviderFactory.PROVIDER_TYPES}

    @override
    def provider_type(self, provider: Provider) -> type[AbstractProvider[Any, Any]]:
        """Return the provider type for the given provider."""
        return self.PROVIDER_TYPES[provider]

    @override
    def build_provider(
        self,
        config: ProviderConfig,
        config_id: str,
        preserve_credits: bool | None,
    ) -> AbstractProvider[Any, Any]:
        """Build a provider from a configuration dictionary."""
        return self.provider_type(config.provider)(
            config=config,
            config_id=config_id,
            preserve_credits=preserve_credits,
        )

    @override
    def available_providers(self) -> Iterable[Provider]:
        return [provider for provider, instances in self._providers.items() if instances]
