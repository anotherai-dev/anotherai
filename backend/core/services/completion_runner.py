from typing import Any

import structlog

from core.domain.agent import Agent
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
