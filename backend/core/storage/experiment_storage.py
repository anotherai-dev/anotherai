from collections.abc import Collection
from datetime import datetime
from typing import Literal, NamedTuple, Protocol
from uuid import UUID

from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.experiment import Experiment, ExperimentOutput
from core.domain.version import Version

type ExperimentFields = Literal[
    "agent_id",
    "versions.id",
    "inputs.id",
    "outputs.id",
    "versions",
    "inputs",
    "outputs",
    "use_cache",
    "metadata",
]

type ExperimentOutputFields = Literal["output"]


class CompletionIDTuple(NamedTuple):
    completion_id: UUID
    version_id: str
    input_id: str


class CompletionOutputTuple(NamedTuple):
    output: AgentOutput
    cost_usd: float | None
    duration_seconds: float | None


class ExperimentStorage(Protocol):
    async def create(self, experiment: Experiment, agent_uid: int | None = None) -> None: ...

    async def set_result(self, experiment_id: str, result: str) -> None: ...

    # TODO: deprecate
    async def add_run_id(self, experiment_id: str, run_id: str) -> None: ...

    async def delete(self, experiment_id: str) -> None: ...

    async def list_experiments(
        self,
        agent_uid: int | None,
        since: datetime | None,
        limit: int,
        offset: int = 0,
    ) -> list[Experiment]: ...

    async def count_experiments(self, agent_uid: int | None, since: datetime | None) -> int: ...

    async def get_experiment(
        self,
        experiment_id: str,
        include: set[ExperimentFields] | None = None,
        version_ids: Collection[str] | None = None,
        input_ids: Collection[str] | None = None,
    ) -> Experiment: ...

    async def add_inputs(self, experiment_id: str, inputs: list[AgentInput]) -> set[str]:
        """Adds the inputs to the experiment. Returns a list of the input ids that were inserted"""
        ...

    async def add_versions(self, experiment_id: str, versions: list[Version]) -> set[str]:
        """Adds the versions to the experiment. Returns a list of the version ids that were inserted"""
        ...

    async def add_completions(
        self,
        experiment_id: str,
        completions: list[CompletionIDTuple],
    ) -> set[UUID]:
        """Adds a completion to an experiment. If an output is provided, the completion is marked as completed.
        Raises a DuplicateValueError if a completion already exists for the experiment, input and version."""
        ...

    async def start_completion(self, experiment_id: str, completion_id: UUID) -> None:
        """Mark a completion as started in an experiment.
        If the completion is already started, raises a DuplicateValueError"""
        ...

    async def fail_completion(self, experiment_id: str, completion_id: UUID) -> None:
        """Mark a completion as failed in an experiment.
        The completion can be started again"""
        ...

    async def add_completion_output(
        self,
        experiment_id: str,
        completion_id: UUID,
        output: CompletionOutputTuple,
    ) -> None:
        """Sets the output for a completion in an experiment. Completion is marked as completed.
        Raises a DuplicateValueError if the completion is already completed."""
        ...

    async def list_experiment_inputs(
        self,
        experiment_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AgentInput]: ...

    async def list_experiment_versions(
        self,
        experiment_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Version]: ...

    async def list_experiment_outputs(
        self,
        experiment_id: str,
        version_ids: Collection[str] | None = None,
        input_ids: Collection[str] | None = None,
        include: set[ExperimentOutputFields] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExperimentOutput]:
        """Returns the completions of an experiment.
        Raises an error if the version_ids or input_ids are not found in the experiment."""
        ...
