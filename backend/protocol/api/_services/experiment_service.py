import asyncio
from typing import final

from core.domain.agent import Agent
from core.domain.exceptions import ObjectNotFoundError
from core.storage.agent_storage import AgentStorage
from core.storage.annotation_storage import AnnotationStorage, TargetFilter
from core.storage.completion_storage import CompletionStorage
from core.storage.experiment_storage import ExperimentStorage
from core.utils.background import add_background_task
from protocol.api._api_models import CreateExperimentRequest, Experiment, Page
from protocol.api._services.conversions import create_experiment_to_domain, experiment_from_domain


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

    async def get_experiment(self, experiment_id: str) -> Experiment:
        exp = await self.experiment_storage.get_experiment(experiment_id)

        res = await asyncio.gather(
            self.annotation_storage.list(
                target=TargetFilter(completion_id=set(exp.run_ids)),
                context=None,
                since=None,
                limit=100,
            ),
            self.completion_storage.completions_by_ids(exp.run_ids, exclude={"traces"}),
        )

        # getting annotations as needed
        return experiment_from_domain(exp, res[1], res[0])

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
        items = [experiment_from_domain(e, [], []) for e in exp]
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
        return experiment_from_domain(domain_exp, [], [])
