import logging
import random
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any, NoReturn, Protocol, final

from structlog.contextvars import bind_contextvars

from core.domain.exceptions import InternalError, NoProviderSupportingModelError
from core.domain.fallback_option import FallbackOption
from core.domain.metrics import send_counter
from core.domain.models.model_data import FinalModelData, ModelData
from core.domain.models.providers import Provider
from core.domain.models.utils import get_model_data
from core.domain.tenant_data import ProviderSettings
from core.domain.typology import IOTypology
from core.domain.version import Version
from core.providers._base.abstract_provider import AbstractProvider
from core.providers._base.provider_error import ProviderError, StructuredGenerationError
from core.providers._base.provider_options import ProviderOptions
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.runners.utils import sanitize_model_and_provider
from core.utils.dump import safe_dump_pydantic_model

type PipelineProviderData = tuple[AbstractProvider[Any, Any], ProviderOptions, ModelData]


class ProviderPipelineBuilder(Protocol):
    def __call__(
        self,
        provider: AbstractProvider[Any, Any],
        model_data: FinalModelData,
        is_structured_generation_enabled: bool,
    ) -> PipelineProviderData: ...


# By default we try providers in order
# This allows maxing out the first key before attacking the following ones
# which is good to create grounds to request quota increase. The downside is that
# there is some added latency when the first providers return 429s but it should
# be minimal.
#
# However, some providers do not return an immediate 429 on quota reached but instead
# start throttling requests or treating them with a lower priority, making inference
# way longer. To circumvent that, we use a round robin strategy, aka we shuffle the array
# before iterating over it.
_round_robin_similar_providers: set[Provider] = {
    Provider.FIREWORKS,
}

_logger = logging.getLogger("ProviderPipeline")


@final
class ProviderPipeline:
    def __init__(
        self,
        agent_id: str,
        version: Version,
        custom_configs: list[ProviderSettings] | None,
        factory: AbstractProviderFactory,
        builder: ProviderPipelineBuilder,
        typology: IOTypology,
        use_fallback: FallbackOption,
    ):
        self._factory = factory
        self._version = version

        model, provider = sanitize_model_and_provider(version.model, version.provider)
        self._original_model_data = get_model_data(model)
        self._original_provider = provider

        self._custom_configs = custom_configs
        self.errors: list[ProviderError] = []
        self.builder = builder
        self._force_structured_generation = version.use_structured_generation
        self._last_error_was_structured_generation = False
        self._typology = typology
        self._has_used_model_fallback: bool = False
        self._model_fallback_disabled = use_fallback == "never"
        self._fallback_models = use_fallback if isinstance(use_fallback, list) else None

        self._found_a_provider = False
        self._agent_id = agent_id

    @property
    def _retry_on_same_provider(self) -> bool:
        """Whether we should retry on the same provider"""
        if not self.errors:
            return True
        return self.errors[-1].code in {"rate_limit", "invalid_provider_config"}

    @property
    def _retry_on_different_provider(self) -> bool:
        """Whether we should retry on a different provider and on the same model"""
        if not self.errors:
            return True
        return self.errors[-1].should_try_next_provider

    def _raise_no_provider_supporting_model(self) -> NoReturn:
        possible_providers_and_env_vars = [
            (p, self._factory.provider_type(p).required_env_vars()) for p, _ in self._original_model_data.providers
        ]
        if not possible_providers_and_env_vars:
            # That should never happen, it would mean that there is a hole in our model data mapping
            raise InternalError(
                "No provider found for model",
                extras={"agent_id": self._agent_id, "options": self._version},
            )

        raise NoProviderSupportingModelError(
            model=self._original_model_data.model,
            configured_providers=list(self._factory.available_providers()),
            possible_providers=possible_providers_and_env_vars,
        )

    def raise_on_end(self) -> NoReturn:
        if not self.errors and not self._found_a_provider:
            return self._raise_no_provider_supporting_model()
        # TODO: metric
        raise (
            self.errors[0]
            if self.errors
            else InternalError(
                "No provider found",
                extras={"agent_id": self._agent_id, "options": self._version},
            )
        )

    def _pick_fallback_model(self, e: ProviderError) -> FinalModelData | None:  # noqa: C901
        """Selects the fallback model to use based on the error code"""
        if self._model_fallback_disabled:
            return None

        if self._fallback_models is not None:
            # User provided fallback models
            if not self._fallback_models:
                # We have already all the provided fallback models
                return None

            fallback_model = self._fallback_models.pop(0)
            return get_model_data(fallback_model)

        # Below is the auto fallback logic
        # We skip if either:
        # - the model has no fallback
        # - we have already used a fallback
        if not self._original_model_data.fallback or self._has_used_model_fallback:
            return None

        match e.code:
            case "content_moderation":
                fallback_model = self._original_model_data.fallback.content_moderation
            case "structured_generation_error" | "invalid_generation" | "failed_generation":
                fallback_model = self._original_model_data.fallback.structured_output
            case "max_tokens_exceeded":
                fallback_model = self._original_model_data.fallback.context_exceeded
            case "invalid_file" | "max_tool_call_iteration" | "task_banned" | "bad_request" | "agent_run_failed":
                return None
            case "rate_limit" | "provider_internal_error" | "provider_unavailable" | "read_timeout" | "timeout":
                fallback_model = self._original_model_data.fallback.rate_limit
            case _:
                fallback_model = (
                    self._original_model_data.fallback.unkwown_error or self._original_model_data.fallback.rate_limit
                )

        if not fallback_model:
            return None

        fallback_model_data = get_model_data(fallback_model)
        if fallback_model_data.is_not_supported_reason(self._typology):
            _logger.warning(
                "Fallback model is not supported for the task typology",
                extra={
                    "model": self._version.model,
                    "fallback_model": fallback_model,
                    "typology": safe_dump_pydantic_model(self._typology),
                },
            )
            return None

        return fallback_model_data

    @contextmanager
    def wrap_provider_call(self, provider: AbstractProvider[Any, Any]):
        try:
            yield
        except StructuredGenerationError as e:
            self._last_error_was_structured_generation = True
            e.capture_if_needed()
            if self._force_structured_generation is None:
                # In this case we will retry without structured generation
                return
            raise e
        except ProviderError as e:
            e.capture_if_needed()
            self.errors.append(e)

            if provider.is_custom_config:
                # In case of custom configs, we always retry
                return

            # Otherwise we retry only if the error should be retried on the next provider
            # or if we haven't consumed the fallback to model or if we have some leftover fallback models
            if e.should_try_next_provider or self._has_used_model_fallback is False or self._fallback_models:
                return

            # Or we just raise the first error to be consistent with the other errors
            raise self.errors[0] from None

    def _should_retry_without_structured_generation(self):
        # We pop the flag and set the force structured generation to false to
        # trigger a provider without structured gen only
        if self._last_error_was_structured_generation and self._force_structured_generation is None:
            self._force_structured_generation = False
            self._last_error_was_structured_generation = False
            return True

        return False

    def _use_structured_output(self, model_data: ModelData):
        if self._force_structured_generation is not None:
            return self._force_structured_generation
        return model_data.supports_structured_output

    def _build(self, provider: AbstractProvider[Any, Any], model_data: FinalModelData) -> PipelineProviderData:
        return self.builder(provider, model_data, self._use_structured_output(model_data))

    def _iter_with_structured_gen(
        self,
        provider: AbstractProvider[Any, Any],
        model_data: FinalModelData,
    ) -> Iterator[PipelineProviderData]:
        self._found_a_provider = True
        bind_contextvars(provider=provider, model=model_data.model)
        yield self._build(provider, model_data)

        if self._should_retry_without_structured_generation():
            yield self._build(provider, model_data)

    def _single_provider_iterator(
        self,
        providers: Iterable[AbstractProvider[Any, Any]],
        model_data: FinalModelData,
        provider_type: Provider,
    ) -> Iterator[PipelineProviderData]:
        providers = iter(providers)
        if provider_type not in _round_robin_similar_providers:
            # We yield the first provider first in order to max out quotas
            try:
                provider = next(providers)
            except StopIteration:
                return self._raise_no_provider_supporting_model()
            yield from self._iter_with_structured_gen(provider, model_data)

            # No point in retrying on the same provider if the last error code was not a rate limit
            # Or an invalid provider config
            if not self._retry_on_same_provider:
                return

        # Then we shuffle the rest
        shuffled = list(providers)
        if not shuffled:
            return

        random.shuffle(shuffled)

        for provider in shuffled:
            # We can safely call _iter_with_structured_gen multiple times
            # if the structured generation fails the first time, the retries
            # Without the structured gen will not happen
            yield from self._iter_with_structured_gen(provider, model_data)

            # No point in retrying on the same provider if the last error code was not a rate limit or invalid config
            if not self._retry_on_same_provider:
                return

    def _build_custom_providers(self, configs: list[ProviderSettings]) -> Iterable[AbstractProvider[Any, Any]]:
        for config in configs:
            try:
                decrypted = config.decrypt()
                provider = self._factory.build_provider(decrypted, config.id, preserve_credits=config.preserve_credits)
                yield provider
            except Exception:
                _logger.exception("Failed to build provider with custom config", extra={"config_id": config.id})
                continue

    def _custom_configs_iterator(self) -> Iterator[PipelineProviderData]:
        if not self._custom_configs:
            return

        configs_by_provider: dict[Provider, list[ProviderSettings]] = {}
        for config in self._custom_configs:
            configs_by_provider.setdefault(config.provider, []).append(config)

        for provider, configs in configs_by_provider.items():
            if not self._original_model_data.supported_by_provider(provider):
                continue
            yield from self._single_provider_iterator(
                self._build_custom_providers(configs),
                self._original_model_data,
                provider,
            )

    def provider_iterator(self, raise_at_end: bool = True) -> Iterator[PipelineProviderData]:
        yield from self._custom_configs_iterator()

        if self._original_provider:
            yield from self._single_provider_iterator(
                providers=self._factory.get_providers(self._original_provider),
                model_data=self._original_model_data,
                provider_type=self._original_provider,
            )
            return

        # Iterating over providers
        for provider, provider_data in self._original_model_data.providers:
            # We only use the override for the default pipeline
            # We assume that
            provider_model_data = provider_data.override(self._original_model_data)

            yield from self._single_provider_iterator(
                providers=self._factory.get_providers(provider),
                model_data=provider_model_data,
                provider_type=provider,
            )
            if not self._retry_on_different_provider:
                # If we should not retry on a different provider, we just break the pipeline
                break

        if not self.errors:
            _logger.warning(
                "Reached the end of the provider iterator without errors",
                extra={"model": self._original_model_data.model},
            )
            return

        # Yielding the final model fallback
        while fallback_model_data := self._pick_fallback_model(self.errors[-1]):
            if not self._has_used_model_fallback:
                # First time only we send a metric to count model fallback
                send_counter(
                    "model_fallback",
                    1,
                    original_model=self._original_model_data.model,
                    fallback_model=fallback_model_data.model,
                    error_code=self.errors[-1].code if self.errors else None,
                )
            self._has_used_model_fallback = True

            provider, provider_data = fallback_model_data.providers[0]
            provider_model_data = provider_data.override(fallback_model_data)
            yield from self._single_provider_iterator(
                providers=self._factory.get_providers(provider),
                model_data=provider_model_data,
                provider_type=provider,
            )

        # If we have reached here we should just raise the first error since it would mean that there is no more
        # provider to try
        if raise_at_end:
            return self.raise_on_end()
