from datetime import datetime
from typing import Any, override

import structlog

from core.domain.exceptions import ObjectNotFoundError
from core.domain.experiment import Experiment
from core.storage.experiment_storage import ExperimentStorage
from core.storage.psql._psql_base_storage import AgentLinkedRow, JSONDict, PsqlBaseStorage
from core.storage.psql._psql_utils import map_value
from core.utils.fields import datetime_zero
from core.utils.iter_utils import safe_map

log = structlog.get_logger(__name__)


class PsqlExperimentStorage(PsqlBaseStorage, ExperimentStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "experiments"

    @override
    async def create(self, experiment: Experiment, agent_uid: int | None = None) -> None:
        # Get agent ID from agent_id
        async with self._connect() as connection:
            if not agent_uid:
                agent_uid = await self._agent_uid(connection, experiment.agent_id)

            experiment_row = _ExperimentRow(
                slug=experiment.id,
                agent_uid=agent_uid,
                tenant_uid=self._tenant_uid,
                author_name=experiment.author_name,
                title=experiment.title,
                description=experiment.description,
                result=experiment.result or None,
                run_ids=experiment.run_ids or [],
                metadata=experiment.metadata or {},
            )

            _ = await self._insert(connection, experiment_row)

    @override
    async def set_result(self, experiment_id: str, result: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE experiments
                SET result = $1, updated_at = CURRENT_TIMESTAMP
                WHERE slug = $2
                """,
                result,
                experiment_id,
            )

    @override
    async def add_run_id(self, experiment_id: str, run_id: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE experiments
                SET run_ids = array_append(run_ids, $1), updated_at = CURRENT_TIMESTAMP
                WHERE slug = $2 AND NOT ($1 = ANY(run_ids))
                """,
                run_id,
                experiment_id,
            )

    @override
    async def delete(self, experiment_id: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE experiments
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE tenant_uid = $1 AND slug = $2
                """,
                self._tenant_uid,
                experiment_id,
            )

    def _where_experiments(self, arg_idx: int, agent_uid: int | None, since: datetime | None) -> tuple[str, list[Any]]:
        where: list[str] = ["e.deleted_at IS NULL"]
        arguments: list[Any] = []

        if since is not None:
            where.append(f"e.created_at > ${len(arguments) + arg_idx}")
            arguments.append(map_value(since))
        if agent_uid is not None:
            where.append(f"e.agent_uid = ${len(arguments) + arg_idx}")
            arguments.append(agent_uid)

        return " AND ".join(where), arguments

    @override
    async def list_experiments(
        self,
        agent_uid: int | None,
        since: datetime | None,
        limit: int,
        offset: int = 0,
    ) -> list[Experiment]:
        where, arguments = self._where_experiments(3, agent_uid, since)

        query = f"""
        SELECT e.*, a.slug as agent_slug
        FROM experiments e
        JOIN agents a ON e.agent_uid = a.uid
        WHERE {where}
        ORDER BY e.created_at DESC
        LIMIT $1
        OFFSET $2
        """  # noqa: S608 # OK here since where is defined above

        async with self._connect() as connection:
            rows = await connection.fetch(
                query,
                limit,
                offset,
                *arguments,
            )
            return safe_map(rows, lambda x: self._validate(_ExperimentRow, x).to_domain(), log)

    @override
    async def count_experiments(self, agent_uid: int | None, since: datetime | None) -> int:
        where, arguments = self._where_experiments(1, agent_uid, since)

        query = f"""
        SELECT COUNT(*)
        FROM experiments e
        WHERE {where} AND e.deleted_at IS NULL
        """  # noqa: S608 # OK here since where is defined above

        async with self._connect() as connection:
            count = await connection.fetchval(query, *arguments)
            return count or 0

    @override
    async def get_experiment(self, experiment_id: str) -> Experiment:
        async with self._connect() as connection:
            row = await connection.fetchrow(
                """
                SELECT e.*, a.slug as agent_slug
                FROM experiments e
                JOIN agents a ON e.agent_uid = a.uid
                WHERE e.tenant_uid = $1 AND e.slug = $2 AND e.deleted_at IS NULL
                """,
                self._tenant_uid,
                experiment_id,
            )

            if row is None:
                raise ObjectNotFoundError(f"Experiment not found: {experiment_id}")

            return self._validate(_ExperimentRow, row).to_domain()

    @override
    async def add_inputs()


class _ExperimentRow(AgentLinkedRow):
    """A representation of an experiment row"""

    slug: str = ""
    author_name: str = ""
    title: str = ""
    description: str = ""
    result: str | None = None
    run_ids: list[str] | None = None
    metadata: JSONDict | None = None

    def to_domain(self) -> Experiment:
        return Experiment(
            id=self.slug,
            created_at=self.created_at or datetime_zero(),
            updated_at=self.updated_at or datetime_zero(),
            author_name=self.author_name,
            title=self.title,
            description=self.description,
            result=self.result,
            agent_id=self.agent_slug or "",
            run_ids=self.run_ids or [],
            metadata=self.metadata or None,
        )

class _ExperimentInputRow(BaseModel)
