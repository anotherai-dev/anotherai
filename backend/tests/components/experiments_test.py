import pytest
from httpx import HTTPStatusError

from tests.components._common import IntegrationTestClient


async def test_create_and_annotate_experiment(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call("openai", "gpt-4.1", "openai/completion.json")
    exp = await test_api_client.playground(
        version={"model": "gpt-4.1", "prompt": [{"role": "user", "content": "Hello {{name}}!"}]},
        inputs=[{"variables": {"name": "Toulouse"}}],
    )
    assert "id" in exp

    completions = exp["completions"]
    assert len(completions) == 1
    completion_id = completions[0]["id"]

    # If I add an annotation to the completion, but not the experiment, the 2 are not linked
    _ = await test_api_client.post(
        "/v1/annotations",
        [
            {
                "target": {
                    "completion_id": completion_id,
                },
                "text": "This is a test annotation for the completion",
                "author_name": "Test Author",
            },
        ],
    )
    await test_api_client.wait_for_background()
    exp = await test_api_client.get(f"/v1/experiments/{exp['id']}")
    annotations = exp["annotations"]
    assert len(annotations) == 1
    assert annotations[0]["target"]["completion_id"] == completion_id

    # Now try to add an annotation to the experiment
    _ = await test_api_client.post(
        "/v1/annotations",
        [
            {
                "target": {
                    "experiment_id": exp["id"],
                },
                "text": "This is a test annotation",
                "author_name": "Test Author",
            },
        ],
    )

    exp = await test_api_client.get(f"/v1/experiments/{exp['id']}")
    annotations = exp["annotations"]
    assert len(annotations) == 2

    # Let's try and query the experiment

    exp = await test_api_client.call_tool(
        "query_completions",
        {
            "query": f"SELECT id FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE completions.experiment_id = '{exp['id']}'",  # noqa: S608
        },
    )
    assert len(exp["rows"]) == 1


async def test_create_experiment_user_defined_id(test_api_client: IntegrationTestClient):
    # Create an experiment manually
    exp = await test_api_client.post(
        "/v1/experiments",
        {
            "title": "Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "Test Author",
            "id": "my-experiment-id",
        },
    )
    assert "id" in exp
    assert exp["id"] == "my-experiment-id"

    # I can retrieve it
    retrieved = await test_api_client.get(
        "/v1/experiments/my-experiment-id",
    )
    assert retrieved["id"] == "my-experiment-id"

    # And if I try to create it again, it fails
    with pytest.raises(HTTPStatusError) as e:
        _ = await test_api_client.post(
            "/v1/experiments",
            {
                "title": "Test Experiment",
                "description": "This is a test experiment",
                "agent_id": "test-agent",
                "author_name": "Test Author",
                "id": "my-experiment-id",
            },
        )
    assert e.value.response.status_code == 400
