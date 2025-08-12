from core.domain.models.models import Model
from core.domain.models.providers import Provider
from tests.components._common import IntegrationTestClient


async def test_create_and_retrieve_annotation(test_api_client: IntegrationTestClient):
    # Create a first playground experiment to get a completion
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )
    res = await test_api_client.call_tool(
        "playground",
        {
            "models": f"{Model.GPT_41_MINI_2025_04_14}",
            "author_name": "user",
            "agent_id": "test-agent",
            "inputs": [
                {
                    "variables": {"name": "Toulouse"},
                },
            ],
            "prompts": [
                [
                    {"role": "user", "content": "What is the capital of the country that has {{ name }}?"},
                ],
            ],
            "experiment_title": "Capital Extractor Test Experiment",
        },
    )
    # This will create a single completion
    assert len(res["completions"]) == 1, "sanity"
    completion_id = res["completions"][0]["id"]

    await test_api_client.wait_for_background()

    # Now create an annotation that targets the run
    tool_res = await test_api_client.call_tool(
        "add_annotations",
        {
            "annotations": [
                {
                    "target": {"completion_id": completion_id},
                    "text": "This is a test annotation",
                    "author_name": "user",
                },
            ],
        },
    )
    assert tool_res == {"result": "success"}

    # I should be able to list all annotations and retrieve it
    anns = await test_api_client.get("/v1/annotations")
    assert len(anns["items"]) == 1
    assert anns["items"][0]["target"]["completion_id"] == completion_id
    assert anns["items"][0]["context"]["agent_id"] == "test-agent"

    # I can call the tool call and filter by agent_id
    anns = await test_api_client.call_tool(
        "get_annotations",
        {
            "agent_id": "test-agent",
        },
    )
    assert len(anns["items"]) == 1
