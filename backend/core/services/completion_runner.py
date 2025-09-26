import asyncio
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import structlog

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.cache_usage import CacheUsage
from core.domain.events import EventRouter, StoreCompletionEvent
from core.domain.fallback_option import FallbackOption
from core.domain.tenant_data import TenantData
from core.domain.version import Version
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.runners.agent_completion_builder import AgentCompletionBuilder
from core.runners.runner import Runner
from core.storage.completion_storage import CompletionStorage
from core.utils.coroutines import capture_errors

_log = structlog.get_logger(__name__)


class CompletionRunner:
    def __init__(
        self,
        tenant: TenantData,
        completion_storage: CompletionStorage,
        provider_factory: AbstractProviderFactory,
        event_router: EventRouter,
    ):
        self._completion_storage = completion_storage
        self._tenant = tenant
        self._provider_factory = provider_factory
        self._event_router = event_router

    async def _from_cache(
        self,
        completion_id: UUID,
        agent: Agent,
        version: Version,
        input: AgentInput,
        metadata: dict[str, Any],
        timeout_seconds: float,
    ) -> AgentCompletion | None:
        async with asyncio.timeout(
            timeout_seconds + 0.050,  # Just a safety, the underlying client should timeout on its own
        ):
            from_cache = await self._completion_storage.cached_completion(
                version_id=version.id,
                input_id=input.id,
                timeout_seconds=timeout_seconds,
            )
            if not from_cache:
                return None
            completion = AgentCompletion(
                id=completion_id,
                agent=agent,
                version=version,
                agent_input=input,
                agent_output=from_cache.agent_output,
                messages=[],
                traces=[],
                metadata={
                    **metadata,
                    "anotherai/cached_from": from_cache.id,
                    "anotherai/original_cost_usd": from_cache.cost_usd,
                    "anotherai/original_duration_seconds": from_cache.duration_seconds,
                },
                cost_usd=0,
                duration_seconds=0,
            )
            self._event_router(StoreCompletionEvent(completion=completion))
            return completion

    async def check_cache(
        self,
        completion_id: UUID,
        agent: Agent,
        version: Version,
        input: AgentInput,
        use_cache: CacheUsage | None,
        metadata: dict[str, Any],
        timeout_seconds: float = 0.150,
    ) -> AgentCompletion | None:
        use_cache = use_cache or CacheUsage.AUTO
        # Attempt to retrieve from cache if possible
        if use_cache == CacheUsage.ALWAYS or (use_cache == CacheUsage.AUTO and version.should_use_auto_cache()):
            with capture_errors(_log, "Error fetching cached output"):
                completion = await self._from_cache(
                    completion_id,
                    agent,
                    version,
                    input,
                    metadata,
                    timeout_seconds=timeout_seconds,
                )
                if completion:
                    return completion
        return None

    async def prepare(
        self,
        agent: Agent,
        version: Version,
        start_time: float,
        input: AgentInput,
        metadata: dict[str, Any],
        timeout: float | None,  # noqa: ASYNC109
        use_fallback: FallbackOption,
        completion_id: UUID,
        conversation_id: str | None,
    ):
        runner = Runner(
            tenant_slug=self._tenant.slug,
            custom_configs=self._tenant.providers,
            agent=agent,
            version=version,
            metadata=metadata,
            metric_tags={},
            provider_factory=self._provider_factory,
            timeout=timeout or 240,
            use_fallback=use_fallback,
        )
        builder = await runner.prepare_completion(
            agent_input=input,
            start_time=start_time,
            completion_id=completion_id,
            metadata=metadata,
            conversation_id=conversation_id,
        )
        return runner, builder

    @contextmanager
    def _store_async(self, builder: AgentCompletionBuilder):
        try:
            yield
        finally:
            # Store the run
            if builder.completion:
                self._event_router(StoreCompletionEvent(completion=builder.completion))
            else:
                _log.error("No completion to store", completion_id=builder.id)

    async def run(
        self,
        runner: Runner,
        builder: AgentCompletionBuilder,
    ) -> AgentCompletion:
        with self._store_async(builder):
            return await runner.run(builder)

    async def stream(
        self,
        runner: Runner,
        builder: AgentCompletionBuilder,
    ):
        with self._store_async(builder):
            async for o in runner.stream(builder):
                yield o
