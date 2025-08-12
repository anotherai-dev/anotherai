from tests.components._common import IntegrationTestClient


async def test_create_views_and_dashboards(test_api_client: IntegrationTestClient):
    v1 = await test_api_client.post(
        "/v1/views",
        json={
            "title": "My bar graph",
            "query": "SELECT * FROM completions",
            "graph": {
                "type": "bar",
                "x": {"field": "my_column"},
                "y": [{"field": "my_column", "label": "My column", "unit": "USD"}],
            },
        },
    )
    assert v1["id"]
    v2 = await test_api_client.post(
        "/v1/views",
        json={
            "title": "My bar graph",
            "query": "SELECT * FROM completions",
        },
    )
    assert v2["id"]

    views = await test_api_client.get("/v1/views")
    assert len(views["items"]) == 1
    assert views["items"][0]["id"] == ""
    assert [v["id"] for v in views["items"][0]["views"]] == [v1["id"], v2["id"]]

    # Now I can create a folder and add the views to it
    folder = await test_api_client.post(
        "/v1/view-folders",
        json={
            "name": "My folder",
        },
    )
    assert folder["id"]
    assert folder["name"] == "My folder"

    _ = await test_api_client.patch(
        f"/v1/views/{v1['id']}",
        json={
            "folder_id": folder["id"],
        },
    )

    views = await test_api_client.get("/v1/views")
    assert len(views["items"]) == 2
    assert views["items"][0]["id"] == folder["id"]
    assert views["items"][0]["name"] == "My folder"
    assert [v["id"] for v in views["items"][0]["views"]] == [v1["id"]]

    assert views["items"][1]["id"] == ""
    assert [v["id"] for v in views["items"][1]["views"]] == [v2["id"]]

    # Finally to remove the view from the folder I call the patch endpoint with an empty folder_id
    _ = await test_api_client.patch(
        f"/v1/views/{v1['id']}",
        json={
            "folder_id": "",
        },
    )
    views = await test_api_client.get("/v1/views")
    assert len(views["items"]) == 2
    assert views["items"][0]["id"] == folder["id"]
    assert views["items"][0]["views"] == []
