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
    res = await test_api_client.playground(
        version={
            "model": Model.GPT_41_MINI_2025_04_14,
            "prompt": [
                {"role": "user", "content": "What is the capital of the country that has {{ name }}?"},
            ],
        },
        inputs=[
            {
                "variables": {"name": "Toulouse"},
            },
        ],
    )
    experiment_id = res["id"]

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
                    "context": {"experiment_id": experiment_id},
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

    # Check that it's also available in Clickhouse
    res = await test_api_client.call_tool(
        "query_completions",
        {
            "query": "SELECT * FROM annotations WHERE agent_id = 'test-agent'",
        },
    )
    assert res
    assert len(res["rows"]) == 1
    assert res["rows"][0]["agent_id"] == "test-agent"
    assert res["rows"][0]["completion_id"] == completion_id, "completion_id mismatch"
    assert res["rows"][0]["experiment_id"] == experiment_id, "experiment_id mismatch"

    # Let's add an annotation to the experiment
    await test_api_client.call_tool(
        "add_annotations",
        {
            "annotations": [{"target": {"experiment_id": experiment_id}, "text": "Ann XP", "author_name": "user"}],
        },
    )
    await test_api_client.wait_for_background()

    res = await test_api_client.call_tool(
        "query_completions",
        {
            "query": "SELECT completion_id, experiment_id FROM annotations WHERE agent_id = 'test-agent'",
        },
    )
    assert res
    assert len(res["rows"]) == 2

    # If I get the experiment I should get both
    exp = await test_api_client.get(f"/v1/experiments/{experiment_id}")
    assert len(exp["annotations"]) == 2
