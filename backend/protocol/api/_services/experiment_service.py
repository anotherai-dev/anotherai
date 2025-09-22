import asyncio
import time
from collections.abc import Collection
from typing import Any, final

from core.domain.agent import Agent
from core.domain.cache_usage import CacheUsage
from core.domain.exceptions import ObjectNotFoundError
from core.storage.agent_storage import AgentStorage
from core.storage.annotation_storage import AnnotationStorage, TargetFilter
from core.storage.completion_storage import CompletionStorage
from core.storage.experiment_storage import ExperimentStorage
from core.utils.background import add_background_task
from core.utils.hash import HASH_REGEXP_32
from protocol.api._api_models import CreateExperimentRequest, Experiment, MCPExperiment, Page
from protocol.api._services.conversions import (
    create_experiment_to_domain,
    experiment_from_domain,
    mcp_experiment_from_domain,
)
from protocol.api._services.utils_service import IDType, sanitize_ids


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
    ) -> MCPExperiment:
        # we need a list here because we want to order the returned outputs the same way the versions and inputs
        # are ordered
        sanitized_versions = list(sanitize_ids(version_ids, IDType.VERSION, HASH_REGEXP_32)) if version_ids else None
        sanitized_inputs = list(sanitize_ids(input_ids, IDType.INPUT, HASH_REGEXP_32)) if input_ids else None

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

        exp = await self.experiment_storage.get_experiment(
            experiment_id,
            include={"versions", "inputs"},
            version_ids=version_ids,
            input_ids=input_ids,
        )

        return mcp_experiment_from_domain(
            exp,
            f"""SELECT id, input_id, version_id, output_id, output_messages, output_error, COALESCE(cost_usd, metadata['anotherai/original_cost_usd']), COALESCE(duration_seconds, metadata['anotherai/original_duration_seconds'])
            FROM completions WHERE metadata['anotherai/experiment_id'] = '{exp.id}'""",  # noqa: S608 # exp.id is sanitized
        )

    async def get_experiment(
        self,
        experiment_id: str,
        version_ids: Collection[str] | None,
        input_ids: Collection[str] | None,
    ) -> Experiment:
        exp = await self.experiment_storage.get_experiment(
            experiment_id,
            include={"versions", "inputs", "outputs"},
            version_ids=version_ids,
            input_ids=input_ids,
        )

        annotations = await self.annotation_storage.list(
            target=TargetFilter(completion_id=set(exp.run_ids)),
            context=None,
            since=None,
            limit=100,
        )

        # getting annotations as needed
        return experiment_from_domain(exp, annotations)

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
