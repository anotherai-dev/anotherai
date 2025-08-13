from core.domain.models.models import Model
from core.domain.models.providers import Provider
from tests.components._common import IntegrationTestClient


async def test_create_and_reuse_input(test_api_client: IntegrationTestClient):
    # Create an input

    response = await test_api_client.mcp.call_tool(
        "create_input",
        arguments={
            "input": {
                "agent_id": "test-agent",
                "variables": {
                    "city": "Paris",
                },
            },
        },
    )
    assert response.data == "Successfully created input 837e2a04888bf5051e693d0da96dfd21"

    # Now I can re-use in the playground
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )
    res = await test_api_client.call_tool(
        "playground",
        arguments={
            "models": Model.GPT_41_MINI_2025_04_14,
            "agent_id": "test-agent",
            "completion_query": "SELECT * FROM inputs WHERE input_id = '837e2a04888bf5051e693d0da96dfd21'",
            "prompts": [
                [
                    {"role": "user", "content": "What is the capital of the country that has {{ city }}?"},
                ],
            ],
            "experiment_title": "Capital Extractor Test Experiment",
            "author_name": "user",
        },
    )
    completions = res["completions"]
    assert len(completions) == 1
    await test_api_client.wait_for_background()
