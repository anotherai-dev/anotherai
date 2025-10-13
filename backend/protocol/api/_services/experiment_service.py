import asyncio
import time
from collections.abc import Collection
from typing import Any, Literal, cast, final

from core.domain.agent import Agent
from core.domain.annotation import Annotation
from core.domain.cache_usage import CacheUsage
from core.domain.exceptions import ObjectNotFoundError
from core.storage.agent_storage import AgentStorage
from core.storage.annotation_storage import AnnotationStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.experiment_storage import ExperimentFields, ExperimentStorage
from core.utils.background import add_background_task
from protocol.api._api_models import CreateExperimentRequest, Experiment, Page
from protocol.api._services.conversions import (
    create_experiment_to_domain,
    experiment_from_domain,
)
from protocol.api._services.ids_service import IDType, sanitize_ids


@final
class ExperimentService:
    def __init__(
        self,
        experiment_storage: ExperimentStorage,
        agent_storage: AgentStorage,
        completion_storage: CompletionStorage,
        annotation_storage: AnnotationStorage,
    ):
        self.experiment_storage = experiment_storage
        self.agent_storage = agent_storage
        self.completion_storage = completion_storage
        self.annotation_storage = annotation_storage

    async def wait_for_experiment(
        self,
        experiment_id: str,
        version_ids: list[str] | None,
        input_ids: list[str] | None,
        max_wait_time_seconds: float,
        include: set[ExperimentFields | Literal["annotations"]] | None,
    ) -> Experiment:
        # we need a list here because we want to order the returned outputs the same way the versions and inputs
        # are ordered
        sanitized_versions = list(sanitize_ids(version_ids, IDType.VERSION)) if version_ids else None
        sanitized_inputs = list(sanitize_ids(input_ids, IDType.INPUT)) if input_ids else None

        start_time = time.time()

        while time.time() - start_time < max_wait_time_seconds:
            # First fetch completions to check that all are properly completed
            completions = await self.experiment_storage.list_experiment_completions(
                experiment_id,
                version_ids=sanitized_versions,
                input_ids=sanitized_inputs,
            )
            if all(c.completed_at for c in completions):
                break

            # TODO: check that all completions are properly started

            await asyncio.sleep(5)

        return await self.get_experiment(
            experiment_id,
            version_ids=sanitized_versions,
            input_ids=sanitized_inputs,
            include=include or {"outputs", "versions", "inputs", "annotations"},
        )

    async def get_experiment(
        self,
        experiment_id: str,
        version_ids: Collection[str] | None,
        input_ids: Collection[str] | None,
        include: set[ExperimentFields | Literal["annotations"]] | None = None,
    ) -> Experiment:
        exp = await self.experiment_storage.get_experiment(
            experiment_id,
            include=cast(Collection[ExperimentFields], include) if include else {"outputs", "versions", "inputs"},
            version_ids=version_ids,
            input_ids=input_ids,
        )

        # Fetch reasoning tokens for outputs if they exist
        if exp.outputs:
            completion_ids = [output.completion_id for output in exp.outputs]
            # Get completions with traces from ClickHouse (only exclude agent_id to keep traces)
            completions_with_traces = await self.completion_storage.completions_by_ids(
                completion_ids, exclude={"agent_id"},
            )
            # Create a map of completion_id -> reasoning_token_count
            reasoning_tokens_map = {}
            for comp in completions_with_traces:
                reasoning_tokens = self._calculate_reasoning_tokens_from_traces(comp.traces)
                if reasoning_tokens is not None:
                    reasoning_tokens_map[comp.id] = reasoning_tokens

            # Attach reasoning token counts to experiment outputs
            for output in exp.outputs:
                if output.completion_id in reasoning_tokens_map:
                    output.reasoning_token_count = reasoning_tokens_map[output.completion_id]

        annotations: list[Annotation] = []
        if include is None or "annotations" in include:
            annotations = await self.annotation_storage.list(
                experiment_id=experiment_id,
                completion_id=None,
                agent_id=None,
                since=None,
                limit=200,
            )

        # getting annotations as needed
        return experiment_from_domain(exp, annotations)

    def _calculate_reasoning_tokens_from_traces(self, traces: list[Any] | None) -> float | None:
        """Calculate total reasoning tokens from traces.

        Args:
            traces: List of trace objects

        Returns:
            Total reasoning tokens as float, or None if no reasoning tokens found
        """
        if not traces:
            return None

        total_reasoning_tokens = 0.0
        has_reasoning_field = False

        for trace in traces:
            # Only check LLM traces
            if not hasattr(trace, "kind") or trace.kind != "llm":
                continue

            # Check if trace has usage data
            if not hasattr(trace, "usage") or not trace.usage:
                continue

            # Handle detailed usage structure
            if hasattr(trace.usage, "completion") and trace.usage.completion:
                completion_usage = trace.usage.completion

                # Check if reasoning_token_count field exists
                if hasattr(completion_usage, "reasoning_token_count") and completion_usage.reasoning_token_count is not None:
                    has_reasoning_field = True
                    total_reasoning_tokens += float(completion_usage.reasoning_token_count or 0)

        return total_reasoning_tokens if has_reasoning_field else None

    async def list_experiments(self, agent_id: str | None = None, limit: int = 10, offset: int = 0) -> Page[Experiment]:
        if agent_id:
            agent = await self.agent_storage.get_agent(agent_id)
            agent_uid = agent.uid
        else:
            agent_uid = None
        # Get both experiments and total count
        exp, total_count = await asyncio.gather(
            self.experiment_storage.list_experiments(agent_uid=agent_uid, since=None, limit=limit, offset=offset),
            self.experiment_storage.count_experiments(agent_uid=agent_uid, since=None),
        )
        items = [experiment_from_domain(e, []) for e in exp]
        return Page(items=items, total=total_count)

    async def set_experiment_result(self, experiment_id: str, result: str) -> None:
        await self.experiment_storage.set_result(experiment_id, result)

    async def create_experiment(self, experiment: CreateExperimentRequest) -> Experiment:
        try:
            agent = await self.agent_storage.get_agent(experiment.agent_id)
        except ObjectNotFoundError:
            # Automatically create the agent if it doesn't exist
            agent = Agent(id=experiment.agent_id, uid=0)
            await self.agent_storage.store_agent(agent)

        domain_exp = create_experiment_to_domain(experiment)
        await self.experiment_storage.create(domain_exp, agent_uid=agent.uid)
        add_background_task(self.completion_storage.store_experiment(domain_exp))
        return experiment_from_domain(domain_exp, [])

    async def create_experiment_mcp(
        self,
        experiment_id: str | None,
        title: str,
        description: str | None,
        agent_id: str,
        metadata: dict[str, Any] | None,
        author_name: str,
        use_cache: CacheUsage,
    ) -> Experiment:
        # TODO: handle duplicates
        return await self.create_experiment(
            CreateExperimentRequest(
                id=experiment_id,
                title=title,
                description=description,
                agent_id=agent_id,
                metadata=metadata,
                author_name=author_name,
                use_cache=use_cache,
            ),
        )
