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
    folder_res = await test_api_client.api_client.post(
        "/views/folders",
        json={"name": "Test Folder"},
    )
    assert folder_res.status_code == 201
    folder = folder_res.json()
    folder_id = folder["id"]

    # Create a view with folder assignment using the API
    view_res = await test_api_client.api_client.post(
        "/views",
        json={
            "title": "Test View",
            "query": "SELECT * FROM completions LIMIT 10",
            "folder_id": folder_id,
        },
    )
    assert view_res.status_code == 201
    view = view_res.json()
    view_id = view["id"]

    # Verify the view has the correct folder_id
    get_res = await test_api_client.api_client.get(f"/views/{view_id}")
    assert get_res.status_code == 200
    view_data = get_res.json()
    assert view_data["folder_id"] == folder_id

    # Update the view using MCP tool (which was resetting the folder)
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

    # Verify the folder_id is still preserved after MCP update
    get_res_after = await test_api_client.api_client.get(f"/views/{view_id}")
    assert get_res_after.status_code == 200
    updated_view = get_res_after.json()
    assert updated_view["folder_id"] == folder_id
    assert updated_view["title"] == "Updated Test View"
    assert updated_view["query"] == "SELECT * FROM completions LIMIT 20"
