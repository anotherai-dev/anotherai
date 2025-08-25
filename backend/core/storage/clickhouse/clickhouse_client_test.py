# pyright: reportPrivateUsage=false

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import DatabaseError
from pydantic import BaseModel

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.annotation import Annotation
from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.domain.experiment import Experiment
from core.domain.message import Message
from core.domain.version import Version
from core.storage.clickhouse._models._ch_annotation import ClickhouseAnnotation
from core.storage.clickhouse._models._ch_completion import ClickhouseCompletion
from core.storage.clickhouse._models._ch_experiment import ClickhouseExperiment
from core.storage.clickhouse._models._ch_field_utils import data_and_columns
from core.storage.clickhouse.clickhouse_client import ClickhouseClient
from core.utils.uuid import uuid7
from tests.fake_models import fake_annotation, fake_completion, fake_experiment
from tests.utils import fixtures_json

_insert_settings = {"async_insert": 1, "wait_for_async_insert": 1, "alter_sync": 1}


@pytest.fixture
async def client(clickhouse_client: AsyncClient):
    _ = await clickhouse_client.command("TRUNCATE TABLE completions")  # pyright: ignore [reportUnknownMemberType]
    _ = await clickhouse_client.command("TRUNCATE TABLE annotations")  # pyright: ignore [reportUnknownMemberType]
    _ = await clickhouse_client.command("TRUNCATE TABLE experiments")  # pyright: ignore [reportUnknownMemberType]
    return ClickhouseClient(clickhouse_client, 1)


class TestStoreCompletion:
    async def test_store_completion(self, client: ClickhouseClient):
        completion = fake_completion()
        stored_completion = await client.store_completion(completion, _insert_settings)
        assert stored_completion == completion


class TestStoreAnnotation:
    async def test_store_annotation_basic(self, client: ClickhouseClient):
        """Test storing a basic annotation successfully"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 1))),
        )

        # This should not raise any exceptions
        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_float_metric(self, client: ClickhouseClient):
        """Test storing annotation with float metric value"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 2))),
            metric=Annotation.Metric(name="accuracy", value=0.95),
        )

        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_string_metric(self, client: ClickhouseClient):
        """Test storing annotation with string metric value"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 3))),
            metric=Annotation.Metric(name="category", value="positive"),
        )

        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_bool_metric(self, client: ClickhouseClient):
        """Test storing annotation with boolean metric value"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 4))),
            metric=Annotation.Metric(name="approved", value=True),
        )

        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_no_metric(self, client: ClickhouseClient):
        """Test storing annotation without any metric"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 5))),
            metric=None,
        )

        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_custom_metadata(self, client: ClickhouseClient):
        """Test storing annotation with custom metadata"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 6))),
            metadata={"user_id": "analyst_123", "tags": "review", "priority": "high"},
        )

        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_without_target_completion_id(self, client: ClickhouseClient):
        """Test that storing annotation without target completion_id raises ValueError"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=None, experiment_id="exp-123"),
        )

        with pytest.raises(ValueError, match="Annotation is required to target a completion"):
            await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_without_target(self, client: ClickhouseClient):
        """Test that storing annotation without target raises ValueError"""
        annotation = fake_annotation(target=None)

        with pytest.raises(ValueError, match="Annotation is required to target a completion"):
            await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_no_context(self, client: ClickhouseClient):
        """Test storing annotation without context"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 7))),
            context=None,
        )

        await client.store_annotation(annotation, _insert_settings)

    async def test_store_annotation_with_no_metadata(self, client: ClickhouseClient):
        """Test storing annotation with None metadata"""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 8))),
            metadata=None,
        )

        await client.store_annotation(annotation, _insert_settings)


class TestStoreExperiment:
    async def test_store_experiment_basic(self, client: ClickhouseClient):
        """Test storing a basic experiment successfully"""
        experiment = fake_experiment()

        # This should not raise any exceptions
        await client.store_experiment(experiment, _insert_settings)

    async def test_store_experiment_with_run_ids(self, client: ClickhouseClient):
        """Test storing experiment with multiple run IDs"""
        run_ids = [
            str(uuid7(ms=lambda: 0, rand=lambda: 1)),
            str(uuid7(ms=lambda: 0, rand=lambda: 2)),
            str(uuid7(ms=lambda: 0, rand=lambda: 3)),
        ]
        experiment = fake_experiment(run_ids=run_ids)

        await client.store_experiment(experiment, _insert_settings)

    async def test_store_experiment_empty_run_ids(self, client: ClickhouseClient):
        """Test storing experiment with empty run_ids list"""
        experiment = fake_experiment(run_ids=[])

        await client.store_experiment(experiment, _insert_settings)

    async def test_store_experiment_with_custom_metadata(self, client: ClickhouseClient):
        """Test storing experiment with custom metadata"""
        experiment = fake_experiment(
            metadata={
                "version": "1.0",
                "dataset": "test_data",
                "model_type": "gpt-4",
                "evaluation_type": "sentiment_analysis",
            },
        )

        await client.store_experiment(experiment, _insert_settings)

    async def test_store_experiment_with_no_metadata(self, client: ClickhouseClient):
        """Test storing experiment with None metadata"""
        experiment = fake_experiment(metadata=None)

        await client.store_experiment(experiment, _insert_settings)

    async def test_store_experiment_with_annotations(self, client: ClickhouseClient):
        """Test storing experiment with annotations"""
        annotations = [
            fake_annotation(
                id="ann-1",
                text="First annotation",
                target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 11))),
            ),
            fake_annotation(
                id="ann-2",
                text="Second annotation",
                target=Annotation.Target(completion_id=str(uuid7(ms=lambda: 0, rand=lambda: 12))),
            ),
        ]
        experiment = fake_experiment(annotations=annotations)

        await client.store_experiment(experiment, _insert_settings)

    async def test_store_experiment_with_result(self, client: ClickhouseClient):
        """Test storing experiment with result"""
        experiment = fake_experiment(
            result="Experiment completed successfully with 95% accuracy",
        )

        await client.store_experiment(experiment, _insert_settings)


class TestCompletionsByIds:
    async def test_completions_by_ids_single_completion(self, client: ClickhouseClient):
        completion = fake_completion()

        # Store completion first
        _ = await client.store_completion(completion, _insert_settings)

        result = await client.completions_by_ids([completion.id])

        assert len(result) == 1
        assert result[0].id == completion.id
        assert result[0].duration_seconds == completion.duration_seconds
        assert result[0].cost_usd == completion.cost_usd

    async def test_completions_by_ids_multiple_completions(self, client: ClickhouseClient):
        completion1 = fake_completion(id_rand=1)
        completion2 = fake_completion(id_rand=2)

        # Store both completions
        _ = await client.store_completion(completion1, insert_settings={"async_insert": 1, "wait_for_async_insert": 1})
        _ = await client.store_completion(completion2, insert_settings={"async_insert": 1, "wait_for_async_insert": 1})

        # Retrieve both by IDs
        result = await client.completions_by_ids([completion1.id, completion2.id])

        assert len(result) == 2
        retrieved_ids = {comp.id for comp in result}
        assert retrieved_ids == {completion1.id, completion2.id}

        assert result[0].agent_input.preview
        assert result[0].agent_input.variables is None
        assert result[0].agent_output.preview

    async def test_completions_by_ids_empty_list(self, client: ClickhouseClient):
        result = await client.completions_by_ids([])
        assert result == []

    async def test_completions_by_ids_nonexistent_id(self, client: ClickhouseClient):
        # Use a valid UUID that doesn't exist in the database
        nonexistent_id = str(UUID(int=12345))
        result = await client.completions_by_ids([nonexistent_id])

        assert result == []

    async def test_completions_by_ids_invalid_uuid(self, client: ClickhouseClient):
        # Test with invalid UUID
        with pytest.raises(BadRequestError, match="Invalid UUIDs"):
            _ = await client.completions_by_ids(["invalid-uuid"])

    async def test_completions_by_ids_mixed_valid_invalid(self, client: ClickhouseClient):
        completion = fake_completion()

        # Store one completion
        _ = await client.store_completion(completion, _insert_settings)

        # Test with mix of valid and invalid UUIDs
        with pytest.raises(BadRequestError, match="Invalid UUIDs"):
            _ = await client.completions_by_ids([completion.id, "invalid-uuid"])


class TestCompletionById:
    async def test_completions_by_id(self, client: ClickhouseClient):
        completion = fake_completion()

        # Store completion first
        _ = await client.store_completion(completion, _insert_settings)

        # Retrieve by single ID
        result = await client.completions_by_id(completion.id)
        result.agent = completion.agent

        excluded_fields = {"agent"}
        assert result.model_dump(exclude=excluded_fields) == completion.model_dump(exclude=excluded_fields)

    async def test_completions_by_id_includes_all_fields(self, client: ClickhouseClient):
        completion = fake_completion()

        # Store completion
        _ = await client.store_completion(completion, _insert_settings)

        # Retrieve by ID (should include all fields)
        result = await client.completions_by_id(completion.id)

        # All fields should be present (SELECT *)
        assert result.agent_input.variables == completion.agent_input.variables
        assert len(result.agent_input.messages or []) == len(completion.agent_input.messages or [])
        assert len(result.agent_output.messages or []) == len(completion.agent_output.messages or [])
        assert result.metadata == completion.metadata
        assert len(result.traces) == len(completion.traces)

    async def test_completions_by_id_nonexistent_id(self, client: ClickhouseClient):
        # Use a valid UUID that doesn't exist in the database
        nonexistent_id = str(UUID(int=12345))

        with pytest.raises(ObjectNotFoundError):
            _ = await client.completions_by_id(nonexistent_id)

    async def test_completions_by_id_invalid_uuid(self, client: ClickhouseClient):
        # Test with invalid UUID
        with pytest.raises(BadRequestError, match="Invalid UUID"):
            _ = await client.completions_by_id("invalid-uuid")

    async def test_completions_by_id_with_agent_id_included(self, client: ClickhouseClient):
        completion = fake_completion()

        # Store completion first
        _ = await client.store_completion(completion, _insert_settings)

        # Retrieve by single ID with agent_id included
        result = await client.completions_by_id(completion.id, include={"agent_id"})

        # Should successfully retrieve the completion
        assert result.agent.id == completion.agent.id


@pytest.fixture
async def agent_id_mapping():
    return


class TestTableOptimizations:
    @pytest.fixture(scope="class", autouse=True)
    async def query_fn(self, clickhouse_client: AsyncClient):
        # Inserting the data
        _ = await clickhouse_client.command("TRUNCATE TABLE completions")
        fixture: list[dict[str, Any]] = fixtures_json("db/completions.json")
        domain_models = [AgentCompletion.model_validate(raw) for raw in fixture]
        models = [ClickhouseCompletion.from_domain(1, model) for model in domain_models]
        # Also inserting a row with tenant_uid 2
        models.append(ClickhouseCompletion.from_domain(2, domain_models[0]))

        _, columns = data_and_columns(models[0])
        all_datas = [data_and_columns(model)[0] for model in models]

        _ = await clickhouse_client.insert(
            table="completions",
            column_names=columns,
            data=all_datas,
            settings={"async_insert": 1, "wait_for_async_insert": 1},
        )

    async def test_fetch_by_id(self, clickhouse_client: AsyncClient):
        # Check that fetching by ID by passing a created_at uses the primary key
        _ = await clickhouse_client.command(
            """
EXPLAIN PIPELINE
SELECT *
FROM   completions
WHERE  id = '01933b7c-b2a1-7000-8000-000000000003' and created_at = UUIDv7ToDateTime(toUUID('01933b7c-b2a1-7000-8000-000000000003'))
""",
            settings={"force_primary_key": 1},
        )


async def _load_file[D: BaseModel](
    clickhouse_client: AsyncClient,
    table: str,
    file: str,
    domain_model: type[D],
    conversion: Callable[[int, D], BaseModel],
):
    _ = await clickhouse_client.command(f"TRUNCATE TABLE {table}")
    fixture: list[dict[str, Any]] = fixtures_json(f"clickhouse/{file}.json")
    domain_models = [domain_model.model_validate(raw) for raw in fixture]
    models = [conversion(1, model) for model in domain_models]
    # Also duplicating for tenant_uid 2
    models.append(conversion(2, domain_models[0]))

    _, columns = data_and_columns(models[0], exclude_none=False)
    all_datas = [data_and_columns(model, exclude_none=False)[0] for model in models]
    _ = await clickhouse_client.insert(
        table=table,
        column_names=columns,
        data=all_datas,
        settings={"async_insert": 1, "wait_for_async_insert": 1},
    )
    return domain_models


class TestRawQuery:
    @pytest.fixture(scope="class")
    async def query_fn(self, clickhouse_client: AsyncClient):
        # Truncate all tables
        _ = await _load_file(
            clickhouse_client,
            "completions",
            "completions",
            AgentCompletion,
            ClickhouseCompletion.from_domain,
        )
        _ = await _load_file(
            clickhouse_client,
            "annotations",
            "annotations",
            Annotation,
            ClickhouseAnnotation.from_domain,
        )
        _ = await _load_file(
            clickhouse_client,
            "experiments",
            "experiments",
            Experiment,
            ClickhouseExperiment.from_domain,
        )

        async def query_fn(query: str, tenant_uid: int = 1):
            return await ClickhouseClient(clickhouse_client, tenant_uid).raw_query(query)

        return query_fn

    async def test_agent_id_mapping(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        """Check that the agent_id is mapped to the agent_uid both ways"""
        query_str = "SELECT id, agent_id FROM completions LIMIT 10"

        result = await query_fn(query_str)
        assert result == [
            {"id": UUID("01933b7c-b2a1-7000-8000-000000000003"), "agent_id": "data-analysis-agent"},
            {"id": UUID("01933b7c-b2a1-7000-8000-000000000002"), "agent_id": "code-review-agent"},
            {"id": UUID("01933b7c-b2a1-7000-8000-000000000001"), "agent_id": "customer-support-agent"},
        ]

    async def test_with_agent_filter(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        query_str = "SELECT id FROM completions WHERE agent_id = 'data-analysis-agent'"
        result = await query_fn(query_str)
        assert result == [
            {"id": UUID("01933b7c-b2a1-7000-8000-000000000003")},
        ]

    async def test_group_by_agent_id(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        query_str = "SELECT agent_id, COUNT(*) as count, AVG(cost_usd) as avg_cost_usd, SUM(duration_seconds) as total_duration_seconds FROM completions GROUP BY agent_id"
        result = await query_fn(query_str)
        result.sort(key=lambda x: x["agent_id"])
        assert result == [
            {"agent_id": "code-review-agent", "count": 1, "avg_cost_usd": 0.012, "total_duration_seconds": 3.4},
            {"agent_id": "customer-support-agent", "count": 1, "avg_cost_usd": 0.0045, "total_duration_seconds": 2.2},
            {"agent_id": "data-analysis-agent", "count": 1, "avg_cost_usd": 0.025, "total_duration_seconds": 4.8},
        ]

    async def test_select_star(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        query_str = "SELECT * FROM completions LIMIT 10"
        result = await query_fn(query_str)
        assert len(result) == 3
        assert [r["id"] for r in result] == [
            UUID("01933b7c-b2a1-7000-8000-000000000003"),
            UUID("01933b7c-b2a1-7000-8000-000000000002"),
            UUID("01933b7c-b2a1-7000-8000-000000000001"),
        ]

    async def test_filter_by_metadata(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        query_str = "SELECT id FROM completions WHERE metadata['user_id'] = 'analyst_003'"
        result = await query_fn(query_str)
        assert len(result) == 1
        assert result[0]["id"] == UUID("01933b7c-b2a1-7000-8000-000000000003")

    async def test_select_other_tenant(
        self,
        query_fn: Callable[[str, int], Awaitable[list[dict[str, Any]]]],
    ):
        # Check with a query for a different tenant
        # I get 0 rows when I select from tenant 1
        rows = await query_fn("SELECT * FROM completions WHERE tenant_uid = 2", 1)
        # We could reject here ?
        assert len(rows) == 0

        # I get 1 row when I select from tenant 2
        rows = await query_fn("SELECT * FROM completions WHERE tenant_uid = 2", 2)
        assert len(rows) == 1

    @pytest.mark.parametrize(
        "query_str",
        [
            pytest.param("SHOW users", id="users"),
            pytest.param("USE db", id="use_db"),
            pytest.param("SELECT name FROM system.row_policies", id="row_policies"),
        ],
    )
    async def test_sql_injections(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]], query_str: str):
        with pytest.raises(DatabaseError, match="Not enough privileges"):
            _ = await query_fn(query_str)

    async def test_show_tables(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        result = await query_fn("SHOW TABLES")
        assert len(result) == 3
        assert {r["name"] for r in result} == {"completions", "annotations", "experiments"}

    async def test_select_database(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        result = await query_fn("SELECT database()")
        assert len(result) == 1
        assert result[0]["database()"] == "db_test"

    async def test_select_quota_usage(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        result = await query_fn("SELECT * FROM system.quota_usage")
        # Not sure why clickhouse does not raise here, but we check that we don't get any result
        assert not result

    async def test_aggregate_no_group_by(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        query_str = "SELECT COUNT(*) as total_count FROM completions WHERE agent_id = 'customer-support-agent'"
        result = await query_fn(query_str)
        assert result == [
            {"total_count": 1},
        ]

    async def test_completions_annotated_last_24h(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        """Get completion IDs that have been annotated in the last 24 hours"""
        query_str = """
        SELECT DISTINCT c.id
        FROM completions c
        JOIN annotations a ON c.id = a.completion_id
        WHERE a.created_at >= '2025-01-20T00:00:00'
        ORDER BY c.id
        """
        result = await query_fn(query_str)
        assert len(result) == 3
        expected_ids = {
            UUID("01933b7c-b2a1-7000-8000-000000000001"),
            UUID("01933b7c-b2a1-7000-8000-000000000002"),
            UUID("01933b7c-b2a1-7000-8000-000000000003"),
        }
        assert {r["id"] for r in result} == expected_ids

    async def test_completions_in_specific_experiment(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        """Get completion outputs for runs in a specific experiment"""
        query_str = """
        SELECT c.id, c.output_preview
        FROM completions c
        JOIN experiments e ON has(e.completion_ids, c.id)
        WHERE e.id = 'exp-billing-analysis'
        """
        result = await query_fn(query_str)
        assert len(result) == 1
        assert result[0]["id"] == UUID("01933b7c-b2a1-7000-8000-000000000001")
        assert result[0]["output_preview"] == "Billing issue resolution"

    async def test_high_quality_completions_by_annotations(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        """Find completions with quality scores above 8.0"""
        query_str = """
        SELECT c.id, c.agent_id, a.metric_value_float as quality_score
        FROM completions c
        JOIN annotations a ON c.id = a.completion_id
        WHERE a.metric_name IN ('quality_score', 'methodology_score') AND a.metric_value_float > 8.0
        ORDER BY a.metric_value_float DESC
        """
        result = await query_fn(query_str)
        assert len(result) == 2
        # Should be ordered by quality score descending
        assert result[0]["quality_score"] == 9.2  # quality_score from ann-001
        assert result[0]["agent_id"] == "customer-support-agent"
        assert result[1]["quality_score"] == 8.1  # methodology_score from ann-006
        assert result[1]["agent_id"] == "data-analysis-agent"

    async def test_experiments_with_completion_count(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        """Get experiments with their completion counts"""
        query_str = """
        SELECT e.id, e.agent_id, length(e.completion_ids) as completion_count
        FROM experiments e
        ORDER BY completion_count DESC, e.id
        """
        result = await query_fn(query_str)
        assert len(result) == 4
        # Multi-agent experiment should have the most completions (3)
        assert result[0]["id"] == "exp-multi-agent-comparison"
        assert result[0]["completion_count"] == 3
        # Other experiments should have 1 completion each, ordered by id
        assert result[1]["completion_count"] == 1
        assert result[2]["completion_count"] == 1
        assert result[3]["completion_count"] == 1

    async def test_completions_with_security_annotations(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        """Find completions that have security-related annotations"""
        query_str = """
        SELECT c.id, c.agent_id, a.text, a.metric_value_str as security_impact
        FROM completions c
        JOIN annotations a ON c.id = a.completion_id
        WHERE a.metric_name = 'security_impact'
        """
        result = await query_fn(query_str)
        assert len(result) == 1
        assert result[0]["id"] == UUID("01933b7c-b2a1-7000-8000-000000000002")
        assert result[0]["agent_id"] == "code-review-agent"
        assert result[0]["security_impact"] == "high"
        assert "security vulnerability" in result[0]["text"]

    async def test_average_metrics_by_experiment(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        """Calculate average quality metrics per experiment"""
        query_str = """
        SELECT
            e.id as experiment_id,
            e.agent_id,
            AVG(a.metric_value_float) as avg_quality_score,
            COUNT(a.id) as annotation_count
        FROM experiments e
        JOIN completions c ON has(e.completion_ids, c.id)
        JOIN annotations a ON c.id = a.completion_id
        WHERE a.metric_value_float IS NOT NULL
        GROUP BY e.id, e.agent_id
        ORDER BY avg_quality_score DESC
        """
        result = await query_fn(query_str)
        assert len(result) == 4
        # Should include experiments with numeric metrics, ordered by avg score descending
        # The actual values depend on which annotations belong to which experiments
        for row in result:
            assert row["avg_quality_score"] > 0
            assert row["annotation_count"] > 0
            assert row["experiment_id"] in [
                "exp-billing-analysis",
                "exp-code-quality",
                "exp-data-analysis",
                "exp-multi-agent-comparison",
            ]

    async def test_recent_annotations_with_completion_context(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        """Get recent annotations with completion context"""
        query_str = """
        SELECT
            a.id as annotation_id,
            a.author_name,
            a.text,
            c.id as completion_id,
            c.agent_id as agent_id,
            c.output_preview
        FROM annotations a
        JOIN completions c ON a.completion_id = c.id
        WHERE a.created_at >= '2025-01-20T00:00:00'
        ORDER BY a.created_at DESC
        LIMIT 5
        """
        result = await query_fn(query_str)
        assert len(result) == 5  # Should get 5 most recent annotations from 2025-01-20
        # Check that we have both annotation and completion data
        for row in result:
            assert row["annotation_id"] is not None
            assert row["completion_id"] is not None
            assert row["agent_id"] is not None

    async def test_annotated_completions_in_experiments(
        self,
        query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ):
        """Find completions that are both in experiments and have annotations"""
        query_str = """
        SELECT DISTINCT
            c.id,
            c.agent_id,
            e.id as experiment_id,
            COUNT(a.id) as annotation_count
        FROM completions c
        JOIN experiments e ON has(e.completion_ids, c.id)
        JOIN annotations a ON c.id = a.completion_id
        GROUP BY c.id, c.agent_id, e.id
        ORDER BY annotation_count DESC, c.id
        """
        result = await query_fn(query_str)
        assert len(result) >= 3  # All our completions are in experiments and have annotations
        # Verify structure
        for row in result:
            assert row["annotation_count"] > 0
            assert row["experiment_id"] is not None

    async def test_user_feedback_annotations(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        """Find completions with positive user feedback"""
        query_str = """
SELECT
    c.id,
    c.agent_id,
    c.output_preview,
    a.metric_value_bool as positive_feedback
FROM completions c
JOIN annotations a ON c.id = a.completion_id
WHERE a.metric_name = 'user_feedback' AND a.metric_value_bool = true
        """
        result = await query_fn(query_str)
        assert len(result) == 1
        assert result[0]["positive_feedback"] is True
        assert result[0]["agent_id"] == "customer-support-agent"

    async def test_inputs_from_experiments(self, query_fn: Callable[[str], Awaitable[list[dict[str, Any]]]]):
        query_str = """
SELECT
    input_id,
    input_variables,
    input_messages
FROM completions
WHERE
    id IN (SELECT arrayJoin(completion_ids) FROM experiments WHERE id = 'exp-billing-analysis')
LIMIT 1 BY input_id
        """
        result = await query_fn(query_str)
        assert len(result) == 1
        assert result[0]["input_id"] == b"f0f00f31c1c9358090cc6f36685a9b9d"
        assert json.loads(result[0]["input_variables"]) == {
            "customer_name": "Alice Johnson",
            "ticket_id": "BILL-2025-001",
        }
        assert json.loads(result[0]["input_messages"]) == [
            {
                "role": "user",
                "content": [
                    {
                        "text": "Hi, I have a billing issue with my account.",
                    },
                ],
            },
        ]


class TestAddCompletionToExperiment:
    async def test_add_completion_to_experiment_basic(self, client: ClickhouseClient):
        """Test adding a completion to an experiment updates the completion_ids array."""
        # Create a test experiment
        experiment = fake_experiment(
            id="test-experiment-123",
            agent_id="test-agent",
            run_ids=[],  # Start with empty run_ids
        )

        # Store the experiment first
        await client.store_experiment(experiment, _insert_settings)

        # Generate a completion ID
        completion_id = str(uuid7(ms=lambda: 0, rand=lambda: 1))

        # Add completion to experiment
        await client.add_completion_to_experiment("test-experiment-123", completion_id, {"mutations_sync": 1})

        # Verify the completion was added by querying the database
        result = await client._client.query(
            """
            SELECT completion_ids
            FROM experiments
            WHERE id = {experiment_id:String}
            """,
            parameters={
                "experiment_id": "test-experiment-123",
            },
        )

        assert len(result.result_rows) == 1
        completion_ids = result.result_rows[0][0]  # First row, first column
        assert completion_id in [str(cid) for cid in completion_ids]

    async def test_add_completion_to_experiment_duplicate_ignored(self, client: ClickhouseClient):
        """Test that adding the same completion ID twice doesn't create duplicates."""
        completion_id = str(uuid7(ms=lambda: 0, rand=lambda: 2))

        # Create a test experiment with an existing completion ID
        experiment = fake_experiment(
            id="test-experiment-456",
            agent_id="test-agent",
            run_ids=[completion_id],  # Start with one completion
        )

        # Store the experiment first
        await client.store_experiment(experiment, _insert_settings)

        # Add the same completion ID again
        await client.add_completion_to_experiment("test-experiment-456", completion_id, {"mutations_sync": 1})

        # Verify there's still only one instance of the completion ID
        result = await client._client.query(
            """
            SELECT completion_ids
            FROM experiments
            WHERE tenant_uid = {tenant_uid:UInt32} AND id = {experiment_id:String}
            """,
            parameters={
                "tenant_uid": client.tenant_uid,
                "experiment_id": "test-experiment-456",
            },
        )

        assert len(result.result_rows) == 1
        completion_ids = result.result_rows[0][0]  # First row, first column
        completion_id_strings = [str(cid) for cid in completion_ids]
        assert completion_id_strings.count(completion_id) == 1

    async def test_add_completion_to_experiment_invalid_uuid(self, client: ClickhouseClient):
        """Test that providing an invalid UUID raises BadRequestError."""
        with pytest.raises(BadRequestError, match="Invalid completion UUID"):
            await client.add_completion_to_experiment("test-experiment", "invalid-uuid")


class TestGetVersionById:
    async def test_get_version_by_id_success(self, client: ClickhouseClient):
        """Test successful retrieval of version by ID"""
        # Create and store a completion with a version
        completion = fake_completion(id_rand=1)
        await client.store_completion(completion, _insert_settings)

        # Retrieve the version by completion ID and agent ID
        result_version, completion_id = await client.get_version_by_id(completion.agent.id, completion.id)

        # Verify the returned version matches the original
        assert completion_id == completion.id
        assert result_version.model == completion.version.model
        assert result_version.provider == completion.version.provider
        assert result_version.temperature == completion.version.temperature
        assert result_version.max_output_tokens == completion.version.max_output_tokens
        assert result_version.use_structured_generation == completion.version.use_structured_generation
        assert result_version.tool_choice == completion.version.tool_choice
        assert result_version.prompt == completion.version.prompt

    async def test_get_version_by_id_not_found(self, client: ClickhouseClient):
        """Test ObjectNotFoundError when version/completion doesn't exist"""
        # Use a valid UUID that doesn't exist in the database
        nonexistent_id = str(UUID(int=12345))
        agent_id = "test-agent"

        with pytest.raises(ObjectNotFoundError, match="version"):
            await client.get_version_by_id(agent_id, nonexistent_id)

    async def test_get_version_by_id_with_complex_version(self, client: ClickhouseClient):
        """Test retrieval with complex version object (tools, output schema, etc.)"""
        from core.domain.tool import Tool

        # Create a completion with a more complex version
        complex_version = Version(
            model="gpt-4",
            provider="openai",
            temperature=0.8,
            max_output_tokens=2000,
            use_structured_generation=True,
            tool_choice="auto",
            enabled_tools=[
                Tool(
                    name="calculator",
                    description="A calculator tool",
                    input_schema={"type": "object", "properties": {"expression": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
                ),
            ],
            top_p=0.9,
            presence_penalty=0.1,
            frequency_penalty=0.2,
            parallel_tool_calls=True,
            prompt=[
                Message.with_text("You are an assistant", role="system"),
                Message.with_text("Calculate 2+2", role="user"),
            ],
            output_schema=Version.OutputSchema(
                json_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "number"},
                    },
                    "required": ["result"],
                },
            ),
        )

        completion = fake_completion(id_rand=2)
        # Replace the version with our complex version
        completion = completion.model_copy(update={"version": complex_version})
        await client.store_completion(completion, _insert_settings)

        # Retrieve the version
        result_version, completion_id = await client.get_version_by_id(completion.agent.id, completion.id)
        assert completion_id == completion.id

        # Verify all complex fields are preserved
        assert result_version.model == complex_version.model
        assert result_version.provider == complex_version.provider
        assert result_version.temperature == complex_version.temperature
        assert result_version.max_output_tokens == complex_version.max_output_tokens
        assert result_version.use_structured_generation == complex_version.use_structured_generation
        assert result_version.tool_choice == complex_version.tool_choice
        assert result_version.enabled_tools == complex_version.enabled_tools
        assert result_version.top_p == complex_version.top_p
        assert result_version.presence_penalty == complex_version.presence_penalty
        assert result_version.frequency_penalty == complex_version.frequency_penalty
        assert result_version.parallel_tool_calls == complex_version.parallel_tool_calls
        assert result_version.prompt == complex_version.prompt
        assert result_version.output_schema == complex_version.output_schema

    async def test_get_version_by_id_different_agent(self, client: ClickhouseClient):
        """Test filtering by agent_id - ensure can't access other agent's versions"""
        # Create completion for agent1
        agent1 = Agent(uid=1, id="agent-1", name="Agent 1", created_at=datetime(2025, 1, 1, 1, 1, 1, tzinfo=UTC))
        completion1 = fake_completion(agent=agent1, id_rand=1)
        await client.store_completion(completion1, _insert_settings)

        # Try to access agent1's version with a different agent ID
        wrong_agent_id = "agent-2"

        with pytest.raises(ObjectNotFoundError, match="version"):
            await client.get_version_by_id(wrong_agent_id, completion1.id)
