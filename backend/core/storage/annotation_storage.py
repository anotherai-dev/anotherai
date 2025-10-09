from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.domain.annotation import Annotation


class AnnotationStorage(Protocol):
    async def create(self, annotation: Annotation) -> None:
        pass

    async def list(
        self,
        experiment_id: str | None,
        completion_id: UUID | None,
        agent_id: str | None,
        since: datetime | None,
        limit: int,
    ) -> list[Annotation]: ...

    async def delete(self, annotation_id: str) -> None: ...
