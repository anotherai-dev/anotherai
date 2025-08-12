from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from core.domain.experiment import Experiment as DomainExperiment


class ClickhouseExperiment(BaseModel):
    tenant_uid: int
    created_at: datetime
    id: str
    title: str
    description: str
    result: str | None
    completion_ids: list[UUID]
    agent_id: str
    metadata: dict[str, str]

    @classmethod
    def from_domain(cls, tenant_uid: int, experiment: DomainExperiment) -> "ClickhouseExperiment":
        return cls(
            tenant_uid=tenant_uid,
            created_at=experiment.created_at,
            id=experiment.id,
            title=experiment.title,
            description=experiment.description,
            result=experiment.result,
            completion_ids=[UUID(r) for r in experiment.run_ids],
            agent_id=experiment.agent_id,
            metadata=experiment.metadata or {},
        )
