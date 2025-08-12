# pyright: reportPrivateUsage=false


import pytest

from core.utils.dicts import TwoWayDict
from core.utils.sql import SQLField, SQLSelectField

from ._query_mapper import JSONType, _map_field, _map_json_key, _map_select, _raw_json_mapper, map_query


@pytest.fixture
def agent_uids():
    return TwoWayDict(
        ("agent-1", 100),
        ("agent-2", 200),
        ("agent-3", 300),
    )


_TENANT_UID = 12345


@pytest.mark.parametrize(
    ("original", "mapped"),
    [
        pytest.param(
            "SELECT id, status FROM completions",
            "SELECT uuid AS id, status FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="simple",
        ),
        pytest.param(
            "SELECT agent_id FROM completions",
            "SELECT agent_uid AS agent_id FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="agent_id",
        ),
        pytest.param(
            "SELECT input.id, output.preview FROM completions",
            "SELECT input_id AS input.id, output_preview AS output.preview FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="mapped_fields",
        ),
        pytest.param(
            "SELECT metadata.category, metadata.experiment_id FROM completions",
            "SELECT metadata['category'] AS metadata.category, metadata['experiment_id'] AS metadata.experiment_id FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="metadata",
        ),
        pytest.param(
            "SELECT input.variables.name, input.messages FROM completions",
            "SELECT JSONExtractString(input, 'variables', 'name') AS input.variables.name, simpleJSONExtractString(input, 'messages') AS input.messages FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="input_fields",
        ),
        pytest.param(
            "SELECT output.error.message, output.id FROM completions",
            "SELECT JSONExtractString(output, 'error', 'message') AS output.error.message, output_id AS output.id FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="output_fields",
        ),
        pytest.param(
            "SELECT id FROM completions WHERE status = 'completed'",
            "SELECT uuid AS id FROM completions WHERE tenant_uid = 12345 AND status = 'completed' ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="where_clause",
        ),
        pytest.param(
            "SELECT * FROM completions",
            "SELECT uuid AS id, agent_uid AS agent_id, input, output, version, duration_ds / 10 AS duration_seconds, cost_millionth_usd / 1000000 AS cost_usd, metadata, uuid AS created_at FROM completions WHERE tenant_uid = 12345 ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="star",
        ),
        pytest.param(
            "SELECT agent_id, COUNT(*), AVG(cost_usd) as avg_cost_usd, SUM(duration_seconds) as total_duration_seconds FROM completions GROUP BY agent_id",
            "SELECT agent_uid AS agent_id, count(*), avg(cost_millionth_usd / 1000000) AS avg_cost_usd, sum(duration_ds / 10) AS total_duration_seconds FROM completions WHERE tenant_uid = 12345 GROUP BY agent_id",
            id="group_by_agent_id",
        ),
        pytest.param(
            "SELECT id FROM completions WHERE metadata.user_id = 'analyst_003'",
            "SELECT uuid AS id FROM completions WHERE tenant_uid = 12345 AND metadata['user_id'] = '\"analyst_003\"' ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="metadata_field",
        ),
        pytest.param(
            "SELECT id FROM completions WHERE input.variables.city = 'Sydney'",
            "SELECT uuid AS id FROM completions WHERE tenant_uid = 12345 AND JSONExtractString(input, 'variables', 'city') = 'Sydney' ORDER BY tenant_uid DESC, created_at_date DESC, uuid DESC",
            id="input_where",
        ),
        # Test case for aggregate query without GROUP BY - should not add ORDER BY
        pytest.param(
            "SELECT COUNT(*) as total_count FROM completions WHERE agent_id = 'agent-1'",
            "SELECT count(*) AS total_count FROM completions WHERE tenant_uid = 12345 AND agent_uid = 100",
            id="aggregate_without_group_by",
        ),
        # Test case for aggregate query with multiple aggregates but no GROUP BY
        pytest.param(
            "SELECT COUNT(*) as count, SUM(cost_usd) as total_cost FROM completions",
            "SELECT count(*) AS count, sum(cost_millionth_usd / 1000000) AS total_cost FROM completions WHERE tenant_uid = 12345",
            id="multiple_aggregates_without_group_by",
        ),
    ],
)
def test_map_query(original: str, mapped: str, agent_uids: TwoWayDict[str, int]):
    q, _ = map_query(original, _TENANT_UID, agent_uids)
    assert str(q) == mapped


class TestMapJsonKey:
    """Test cases for the _map_json_key helper function."""

    def test_simple_json_extract(self):
        """Test simple JSON extraction with single key."""
        result = _map_json_key("data", "name", JSONType.STRING)
        assert result == "simpleJSONExtractString(data, 'name')"

    def test_nested_json_extract(self):
        """Test nested JSON extraction with multiple keys."""
        result = _map_json_key("data", "user.profile.name", JSONType.STRING)
        assert result == "JSONExtractString(data, 'user', 'profile', 'name')"

    def test_array_index_json_extract(self):
        """Test JSON extraction with array index."""
        result = _map_json_key("data", "items.0.name", JSONType.STRING)
        assert result == "JSONExtractString(data, 'items', 0, 'name')"

    def test_different_json_types(self):
        """Test different JSON type extractions."""
        assert _map_json_key("data", "age", JSONType.INT) == "simpleJSONExtractInt(data, 'age')"
        assert _map_json_key("data", "score", JSONType.FLOAT) == "simpleJSONExtractFloat(data, 'score')"
        assert _map_json_key("data", "active", JSONType.BOOLEAN) == "simpleJSONExtractBoolean(data, 'active')"
        assert _map_json_key("data", "raw", JSONType.RAW) == "simpleJSONExtractRaw(data, 'raw')"


class TestRawJsonMapper:
    """Test cases for the _raw_json_mapper function."""

    def test_valid_json_parsing(self):
        """Test parsing valid JSON strings."""
        result = _raw_json_mapper('{"name": "test", "value": 123}')
        assert result == {"name": "test", "value": 123}

    def test_json_array_parsing(self):
        """Test parsing JSON arrays."""
        result = _raw_json_mapper('[1, 2, 3, "test"]')
        assert result == [1, 2, 3, "test"]

    def test_json_primitive_parsing(self):
        """Test parsing JSON primitives."""
        assert _raw_json_mapper('"string"') == "string"
        assert _raw_json_mapper("123") == 123
        assert _raw_json_mapper("true") is True
        assert _raw_json_mapper("null") is None

    def test_invalid_json_returns_original(self):
        """Test that invalid JSON returns the original string."""
        result = _raw_json_mapper("invalid json")
        assert result == "invalid json"


_MAP_FIELD_TEST_CASES = [
    pytest.param("id", "uuid", id="id"),
    pytest.param("agent_id", "agent_uid", id="agent_id"),
    pytest.param("version.id", "version_id", id="version.id"),
    pytest.param("version.model", "version_model", id="version.model"),
    pytest.param("input.id", "input_id", id="input.id"),
    pytest.param("input.preview", "input_preview", id="input.preview"),
    pytest.param("metadata", "metadata", id="metadata"),
    pytest.param("metadata.category", "metadata['category']", id="metadata.category"),
]


class TestMapField:
    @pytest.mark.parametrize(("original", "mapped"), _MAP_FIELD_TEST_CASES)
    def test_map_field(self, original: str, mapped: str):
        field = SQLField(column=original)
        actual = _map_field(field, {})
        assert actual.column == mapped


class TestMapSelectField:
    @pytest.mark.parametrize(("original", "mapped"), _MAP_FIELD_TEST_CASES)
    def test_map_select_field(self, original: str, mapped: str):
        field = SQLSelectField(column=original)
        aliases: dict[str, str] = {}
        actual = list(_map_select([field], {}, lambda x: "hello", aliases))
        assert actual[0].column == mapped
        assert aliases == {original: mapped}
