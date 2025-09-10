from tests.components._common import IntegrationTestClient


async def test_documentation_search(test_api_client: IntegrationTestClient):
    await test_api_client.mock_internal_agent(
        content={
            "relevant_documentation_file_paths": [
                "content/docs/foundations",
            ],
        },
    )
    res = await test_api_client.call_tool(
        "search_documentation",
        {
            "query": "Can you explain AnotherAI ?",
        },
    )
    assert res
    assert res["query_results"]
    assert "http://localhost:8000" not in res["query_results"][0]["content_snippet"]
    assert "https://api-staging.anotherai.dev" in res["query_results"][0]["content_snippet"]
