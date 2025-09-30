import json
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from tests.components._common import IntegrationTestClient
from tests.components.run._base import GroqTestCase, OpenAITestCase, ProviderTestCase

_test_cases = [
    pytest.param(OpenAITestCase(), id="openai"),
    pytest.param(GroqTestCase(), id="groq"),
]


@pytest.mark.parametrize("test_case", _test_cases)
async def test_string_completion(test_case: ProviderTestCase, test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        test_case.provider(),
        test_case.model(),
        f"{test_case.provider()}/completion.json",
    )

    client = test_api_client.openai_client()

    response = await client.chat.completions.create(
        model=test_case.model(),
        messages=[{"role": "user", "content": "Hello, world!"}],
    )

    assert response.choices[0].message.content == "The meaning of life is 42"
    assert response.choices[0].cost_usd > 0  # pyright: ignore [reportUnknownMemberType,reportAttributeAccessIssue]

    await test_api_client.wait_for_background()

    # Now fetching the run
    run = await test_api_client.get(f"/v1/completions/{response.id}")
    assert run["id"] == response.id
    assert run["input"] == {
        "id": "a0fb00af4f380639dfe4264ba020d50e",
        "messages": [
            {
                "content": "Hello, world!",
                "role": "user",
            },
        ],
    }
    assert run["version"]["id"] == response.version_id  # pyright: ignore [reportAttributeAccessIssue]
    assert run["output"] == {
        "messages": [
            {
                "content": "The meaning of life is 42",
                "role": "assistant",
            },
        ],
    }
    assert run["cost_usd"]


@pytest.mark.parametrize("test_case", _test_cases)
async def test_structured_output(test_case: ProviderTestCase, test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        test_case.provider(),
        test_case.model(),
        f"{test_case.provider()}/structured_output.json",
    )

    class Output(BaseModel):
        name: str
        age: int

    client = test_api_client.openai_client()

    response = await client.beta.chat.completions.parse(
        model=test_case.model(),
        messages=[{"role": "user", "content": "Hello, world!"}],
        response_format=Output,
    )

    assert response.choices[0].message.parsed == Output(name="John Doe", age=30)
    assert response.choices[0].cost_usd > 0  # pyright: ignore [reportUnknownMemberType,reportAttributeAccessIssue]

    await test_api_client.wait_for_background()

    reqs = test_api_client.get_provider_requests(test_case.provider(), test_case.model())
    assert len(reqs) == 1
    test_case.validate_structured_output_request(json.loads(reqs[0].content), reqs[0])

    # Now fetching the run
    run = await test_api_client.get(f"/v1/completions/{response.id}")
    assert run["id"] == response.id
    assert run["input"] == {
        "id": "a0fb00af4f380639dfe4264ba020d50e",
        "messages": [
            {
                "content": "Hello, world!",
                "role": "user",
            },
        ],
    }
    assert run["output"] == {
        "messages": [
            {
                "content": {"name": "John Doe", "age": 30},
                "role": "assistant",
            },
        ],
    }
    assert run["cost_usd"]

    # Check that I can retrieve the run using a raw query
    query = "SELECT id FROM completions WHERE simpleJSONExtractInt(output_messages, 'age') = 30"
    query_result: list[dict[str, Any]] = await test_api_client.get(f"/v1/completions/query?query={query}")  # pyright: ignore [reportAssignmentType]
    assert len(query_result) == 1
    assert query_result[0]["id"] == response.id


@pytest.mark.parametrize("test_case", _test_cases)
async def test_variablized_files(test_case: ProviderTestCase, test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        test_case.provider(),
        test_case.model(),
        f"{test_case.provider()}/completion.json",
    )

    test_api_client.httpx_mock.add_response(
        url="https://example.com/image.png",
        content=b"image",
    )

    client = test_api_client.openai_client()

    response = await client.chat.completions.create(
        model=test_case.model(),
        messages=[
            {"role": "system", "content": "Hello, world!"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "{{file_url}}",
                        },
                    },
                ],
            },
        ],
        extra_body={
            "input": {
                "file_url": "https://example.com/image.png",
            },
        },
    )
    assert response.choices[0].message.content == "The meaning of life is 42"
    reqs = test_api_client.get_provider_requests(test_case.provider(), test_case.model())
    assert len(reqs) == 1
    test_case.check_includes_image(json.loads(reqs[0].content), reqs[0], "https://example.com/image.png")

    await test_api_client.wait_for_background()
    # Check that the completion's version is valid
    completion = await test_api_client.get(f"/v1/completions/{response.id}")
    version = completion["version"]
    assert version["input_variables_schema"] == {
        "type": "object",
        "properties": {"file_url": {"type": "string"}},
    }
    assert version["prompt"] == [
        {"role": "system", "content": "Hello, world!"},
        {
            "role": "user",
            "content": [
                {
                    "image_url": "{{file_url}}",
                },
            ],
        },
    ]


@pytest.mark.parametrize("test_case", _test_cases)
async def test_parameters(test_case: ProviderTestCase, test_api_client: IntegrationTestClient):
    """Check that parameters are correctly set in the request"""
    test_api_client.mock_provider_call(
        test_case.provider(),
        test_case.model(),
        f"{test_case.provider()}/completion.json",
        is_reusable=True,
    )

    client = test_api_client.openai_client()

    response = await client.chat.completions.create(
        model=test_case.model(),
        messages=[{"role": "user", "content": "Hello, world!"}],
        temperature=0.5,
        max_tokens=100,
        top_p=0.9,
        presence_penalty=0.1,
        frequency_penalty=0.2,
        parallel_tool_calls=False,
    )

    assert response.choices[0].message.content == "The meaning of life is 42"
    assert response.choices[0].cost_usd > 0  # pyright: ignore [reportUnknownMemberType,reportAttributeAccessIssue]

    await test_api_client.wait_for_background()

    def _check(req: httpx.Request):
        body = json.loads(req.content)
        test_case.check_temperature(0.5, body, req)
        test_case.check_max_tokens(100, body, req)
        test_case.check_top_p(0.9, body, req)
        test_case.check_presence_penalty(0.1, body, req)
        test_case.check_frequency_penalty(0.2, body, req)
        test_case.check_parallel_tool_calls(False, body, req)

    reqs = test_api_client.get_provider_requests(test_case.provider(), test_case.model())
    assert len(reqs) == 1
    _check(reqs[0])

    # Do the same with the playground tool
    await test_api_client.playground(
        version={
            "model": test_case.model(),
            "prompt": [],
            "temperature": 0.5,
            "max_output_tokens": 100,
            "top_p": 0.9,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.2,
            "parallel_tool_calls": False,
        },
        inputs=[{"messages": [{"role": "user", "content": "Hello, world!"}]}],
        experiment_kwargs={"use_cache": "never"},  # force to repeat the run
    )

    reqs = test_api_client.get_provider_requests(test_case.provider(), test_case.model())
    assert len(reqs) == 2
    _check(reqs[1])
