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


async def test_create_or_update_view_preserves_folder(test_api_client: IntegrationTestClient):
    """Test that updating a view via MCP preserves its folder assignment."""
    # First, create a folder
    folder = await test_api_client.post(
        "/v1/view-folders",
        json={"name": "Test Folder"},
    )
    folder_id = folder["id"]

    # Create a view with folder assignment using the API
    view = await test_api_client.post(
        "/v1/views",
        json={
            "title": "Test View",
            "query": "SELECT * FROM completions LIMIT 10",
            "folder_id": folder_id,
        },
    )
    view_id = view["id"]

    # Verify the view has the correct folder_id
    views = await test_api_client.get("/v1/views")
    assert len(views["items"]) == 1  # 1 folder
    assert views["items"][0]["id"] == folder_id
    assert len(views["items"][0]["views"]) == 1  # 1 view
    assert views["items"][0]["views"][0]["id"] == view_id

    # Update the view using MCP tool
    mcp_res = await test_api_client.mcp.call_tool(
        "create_or_update_view",
        {
            "view": {
                "id": view_id,
                "title": "Updated Test View",
                "query": "SELECT * FROM completions LIMIT 20",
            },
        },
    )
    assert not mcp_res.is_error

    # Verify the view still has the correct folder_id
    views2 = await test_api_client.get("/v1/views")
    assert len(views2["items"]) == 1  # 1 folder
    assert views2["items"][0]["id"] == folder_id
    assert len(views2["items"][0]["views"]) == 1  # 1 view
    assert views2["items"][0]["views"][0]["id"] == view_id
