import asyncio
from typing import Any

import structlog

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.cache_usage import CacheUsage
from core.domain.fallback_option import FallbackOption
from core.domain.tenant_data import TenantData
from core.domain.version import Version
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.runners.runner import Runner
from core.services.store_completion.completion_storer import CompletionStorer
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.file_storage import FileStorage
from core.utils.background import add_background_task
from core.utils.coroutines import capture_errors
from core.utils.uuid import uuid7

log = structlog.get_logger(__name__)


class CompletionRunner:
    # TODO: we should not need any of that when we use a worker
    def __init__(
        self,
        tenant: TenantData,
        completion_storage: CompletionStorage,
        agent_storage: AgentStorage,
        file_storage: FileStorage,
        provider_factory: AbstractProviderFactory,
    ):
        self._completion_storage = completion_storage
        self._agent_storage = agent_storage
        self._file_storage = file_storage
        self._tenant = tenant
        self._provider_factory = provider_factory
        self._completion_storer = CompletionStorer(completion_storage, agent_storage, file_storage)

    async def _from_cache(
        self,
        completion_id: str,
        agent: Agent,
        version: Version,
        input: AgentInput,
    ) -> AgentCompletion | None:
        async with asyncio.timeout(0.150):  # 150 ms, cached output clickhouse query should exit after 100ms
            agent_output = await self._completion_storage.cached_output(version.id, input.id)
            if not agent_output:
                return None
            return AgentCompletion(
                id=completion_id,
                agent=agent,
                version=version,
                agent_input=input,
                agent_output=agent_output,
                messages=[],
                traces=[],
            )

    async def run(
        self,
        agent: Agent,
        version: Version,
        start_time: float,
        input: AgentInput,
        metadata: dict[str, Any],
        timeout: float | None,  # noqa: ASYNC109
        use_cache: CacheUsage,
        use_fallback: FallbackOption,
        completion_id: str | None,
        conversation_id: str | None,
    ):
        completion_id = completion_id or str(uuid7())

        # Attempt to retrieve from cache if possible
        if use_cache == "always" or (use_cache == "auto" and version.should_use_auto_cache()):
            with capture_errors(log, "Error fetching cached output"):
                completion = await self._from_cache(completion_id, agent, version, input)
                if completion:
                    return completion

        # TODO: cache
        runner = Runner(
            tenant_slug=self._tenant.slug,
            custom_configs=self._tenant.providers,
            agent=agent,
            version=version,
            metadata=metadata,
            metric_tags={},
            provider_factory=self._provider_factory,
            stream_deltas=False,
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
        try:
            return await runner.run(builder)
        finally:
            # Store the run
            if builder.completion:
                add_background_task(self._completion_storer.store_completion(builder.completion))
            else:
                log.error("No completion to store", completion_id=completion_id)
