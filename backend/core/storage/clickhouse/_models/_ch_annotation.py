from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from core.domain.annotation import Annotation


class ClickhouseAnnotation(BaseModel):
    tenant_uid: int
    created_at: datetime
    id: str
    updated_at: datetime
    agent_id: str
    completion_id: UUID
    text: str | None
    metric_name: str | None
    metric_value_float: float | None
    metric_value_str: str | None
    metric_value_bool: bool | None
    metadata: dict[str, str]
    author_name: str

    @classmethod
    def from_domain(cls, tenant_uid: int, annotation: Annotation):
        if not annotation.target or not annotation.target.completion_id:
            raise ValueError("Annotation is required to target a completion")
        completion_id = UUID(annotation.target.completion_id)
        metric_name, metric_value_float, metric_value_str, metric_value_bool = _extract_metric(annotation.metric)

        return cls(
            tenant_uid=tenant_uid,
            created_at=annotation.created_at,
            id=annotation.id,
            updated_at=annotation.updated_at or annotation.created_at,
            agent_id=annotation.context.agent_id if annotation.context and annotation.context.agent_id else "",
            completion_id=completion_id,
            text=annotation.text,
            metric_name=metric_name,
            metric_value_float=metric_value_float,
            metric_value_str=metric_value_str,
            metric_value_bool=metric_value_bool,
            metadata=annotation.metadata or {},
            author_name=annotation.author_name,
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
