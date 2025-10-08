from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from core.domain.annotation import Annotation
from core.utils.uuid import uuid_zero


class ClickhouseAnnotation(BaseModel):
    tenant_uid: int
    created_at: datetime
    id: str
    updated_at: datetime
    agent_id: str
    completion_id: UUID = Field(default_factory=uuid_zero)
    experiment_id: str = ""
    text: str | None = None
    metric_name: str | None = None
    metric_value_float: float | None = None
    metric_value_str: str | None = None
    metric_value_bool: bool | None = None
    metadata: dict[str, str] | None = None
    author_name: str = ""

    @classmethod
    def from_domain(cls, tenant_uid: int, annotation: Annotation):
        completion_id: UUID | None = None
        experiment_id: str | None = None
        agent_id: str = ""

        if annotation.context:
            experiment_id = annotation.context.experiment_id
            agent_id = annotation.context.agent_id or ""
        if annotation.target:
            # We should never have an annotation with an experiment id in both context
            # and target. This should not be checked here so we just override
            if annotation.target.experiment_id:
                experiment_id = annotation.target.experiment_id
            completion_id = annotation.target.completion_id

        metric_name, metric_value_float, metric_value_str, metric_value_bool = _extract_metric(annotation.metric)

        return cls(
            tenant_uid=tenant_uid,
            created_at=annotation.created_at,
            id=annotation.id,
            updated_at=annotation.updated_at or annotation.created_at,
            agent_id=agent_id,
            completion_id=completion_id or uuid_zero(),
            text=annotation.text,
            metric_name=metric_name,
            metric_value_float=metric_value_float,
            metric_value_str=metric_value_str,
            metric_value_bool=metric_value_bool,
            metadata=annotation.metadata or {},
            author_name=annotation.author_name,
            experiment_id=experiment_id or "",
        )


def _extract_metric(metric: Annotation.Metric | None) -> tuple[str | None, float | None, str | None, bool | None]:
    if not metric:
        return None, None, None, None
    if isinstance(metric.value, float):
        return metric.name, metric.value, None, None
    if isinstance(metric.value, str):
        return metric.name, None, metric.value, None
    if isinstance(metric.value, bool):
        return metric.name, None, None, metric.value
    raise ValueError(f"Invalid metric value type: {type(metric.value)}")
