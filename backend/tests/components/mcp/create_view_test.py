import pytest
from fastmcp.exceptions import ToolError

from tests.components._common import IntegrationTestClient


async def test_create_view(test_api_client: IntegrationTestClient):
    # List all views, should be empty
    res = await test_api_client.mcp.call_tool(
        "list_views",
        {},
    )
    assert not res.is_error
    assert res.structured_content
    assert res.structured_content["items"] == []

    res = await test_api_client.mcp.call_tool(
        "create_or_update_view",
        {
            "view": {
                "title": "Conversation Matcher Daily Costs (30 days)",
                "query": "SELECT toDate(created_at) as date, SUM(cost_usd) as daily_cost FROM completions WHERE agent_id = 'conversation-matcher' AND created_at >= now() - INTERVAL 30 DAY GROUP BY date ORDER BY date DESC",
                "graph": {
                    "type": "bar",
                    "x": {"field": "date", "label": "Date"},
                    "y": [{"field": "daily_cost", "label": "Daily Cost", "unit": "$", "color_hex": "#3b82f6"}],
                },
            },
        },
    )
    assert not res.is_error

    res = await test_api_client.mcp.call_tool(
        "list_views",
        {},
    )
    assert not res.is_error
    assert res.structured_content
    assert len(res.structured_content["items"]) == 1


async def test_create_view_with_invalid_json(test_api_client: IntegrationTestClient):
    with pytest.raises(ToolError) as excinfo:
        _ = await test_api_client.mcp.call_tool(
            "create_or_update_view",
            {
                "view": {"bla": "blu"},
            },
        )
    assert "validation errors for" in str(excinfo.value)


async def test_create_view_with_invalid_field(test_api_client: IntegrationTestClient):
    with pytest.raises(ToolError) as excinfo:
        _ = await test_api_client.mcp.call_tool(
            "create_or_update_view",
            {
                "view": {"title": "test", "query": 1},
            },
        )
    assert "validation error for" in str(excinfo.value)
