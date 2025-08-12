from typing import Any, Literal, Protocol

from core.domain.agent_completion import AgentCompletion
from core.domain.annotation import Annotation
from core.domain.experiment import Experiment

type CompletionField = Literal["traces", "agent_id"]


class CompletionStorage(Protocol):
    async def store_completion(self, completion: AgentCompletion) -> AgentCompletion: ...

    async def store_annotation(self, annotation: Annotation): ...

    async def store_experiment(self, experiment: Experiment): ...

    async def add_completion_to_experiment(self, experiment_id: str, completion_id: str): ...

    async def completions_by_ids(
        self,
        completions_ids: list[str],
        exclude: set[CompletionField] | None = None,
    ) -> list[AgentCompletion]: ...

    async def completions_by_id(
        self,
        completion_id: str,
        include: set[CompletionField] | None = None,
    ) -> AgentCompletion: ...

    async def raw_query(self, query: str) -> list[dict[str, Any]]: ...
