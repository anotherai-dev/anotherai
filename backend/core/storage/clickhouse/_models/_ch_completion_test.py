# pyright: reportPrivateUsage=false

from datetime import UTC, datetime
from uuid import UUID

from core.storage.clickhouse._models._ch_completion import DEFAULT_EXCLUDE, ClickhouseCompletion, _Trace
from tests.fake_models import fake_completion, fake_llm_trace


class TestClickhouseCompletion:
    def test_sanity(self):
        completion = fake_completion()
        ch_completion = ClickhouseCompletion.from_domain(1, completion)
        assert ch_completion.model_dump(exclude_unset=True) == ch_completion.model_dump(exclude_none=True)

        domain = ch_completion.to_domain(agent=completion.agent)
        assert domain.model_dump(exclude_unset=True, exclude_none=True) == domain.model_dump(exclude_none=True)
        assert domain.model_dump(exclude_none=True) == completion.model_dump(exclude_none=True)

        assert domain.model_dump(exclude_none=True) == {
            "agent": {
                "created_at": datetime(2025, 1, 1, 1, 1, 1, tzinfo=UTC),
                "id": "hello",
                "name": "hello",
                "uid": 1,
            },
            "agent_input": {
                "id": "44b2da5b47252cca6cf8a28e8579f1e9",
                "messages": [
                    {
                        "content": [
                            {
                                "text": "hello, who are you?",
                            },
                        ],
                        "role": "user",
                    },
                ],
                "preview": "hello",
                "variables": {
                    "name": "John",
                },
            },
            "agent_output": {
                "id": "c152129f278983d40f4ab57ac6da16b9",
                "messages": [
                    {
                        "content": [
                            {
                                "text": "Hello my name is John",
                            },
                        ],
                        "role": "assistant",
                    },
                ],
                "preview": "hello",
            },
            "cost_usd": 1.0,
            "duration_seconds": 1.0,
            "from_cache": False,
            "id": UUID("00000000-0000-7000-0000-000000000001"),
            "messages": [
                {
                    "content": [
                        {
                            "text": "Your name is John",
                        },
                    ],
                    "role": "system",
                },
                {
                    "content": [
                        {
                            "text": "hello, who are you?",
                        },
                    ],
                    "role": "user",
                },
            ],
            "metadata": {
                "array_value": [
                    1,
                    2,
                    3,
                ],
                "bool_value": True,
                "float_value": 1.0,
                "int_value": 1,
                "object_value": {
                    "key": "value",
                },
                "string_value": "hello",
                "user_id": "user_123",
            },
            "source": "api",
            "status": "success",
            "stream": False,
            "traces": [
                {
                    "cost_usd": 3.0,
                    "duration_seconds": 1.0,
                    "kind": "llm",
                    "model": "gpt-4o-mini",
                    "provider": "openai",
                    "usage": {
                        "completion": {
                            "cost_usd": 2.0,
                            "text_token_count": 100.0,
                            "cached_token_count": 100.0,
                            "reasoning_token_count": 100.0,
                        },
                        "prompt": {
                            "cost_usd": 1.0,
                        },
                    },
                },
            ],
            "version": {
                "id": "9a31f2b74fe46bf9191486f1fa54dcdb",
                "max_output_tokens": 100,
                "model": "gpt-4o-mini",
                "prompt": [
                    {
                        "content": [
                            {
                                "text": "Your name is {{name}}",
                            },
                        ],
                        "role": "system",
                    },
                ],
                "provider": "openai",
                "temperature": 0.5,
                "use_structured_generation": False,
            },
        }

    def test_exhaustive(self):
        completion = fake_completion()
        ch_completion = ClickhouseCompletion.from_domain(1, completion)
        assert ch_completion.model_fields_set == set(ClickhouseCompletion.model_fields)


def test_default_exclude():
    field_names = set(ClickhouseCompletion.model_fields.keys())
    assert DEFAULT_EXCLUDE.issubset(field_names)


class TestTrace:
    def test_exhaustive(self):
        trace = fake_llm_trace()
        ch_trace = _Trace.from_domain(trace)
        assert ch_trace.model_fields_set == set(_Trace.model_fields) - {
            "name",
            "tool_input_preview",
            "tool_output_preview",
        }

    def test_sanity(self):
        trace = fake_llm_trace()
        ch_trace = _Trace.from_domain(trace)
        domain = ch_trace.to_domain()
        assert domain == trace

    def test_model_validate(self):
        # A static representation of the trace
        # To make sure updates in the LLMUsage class don't break the validation
        payload = {
            "kind": "llm",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "usage": '{"prompt":{"cost_usd":1.0},"completion":{"text_token_count":100.0,"cost_usd":2.0,"cached_token_count":100.0,"reasoning_token_count":100.0}}',
            "name": "",
            "tool_input_preview": "",
            "tool_output_preview": "",
            "duration_ds": 10,
            "cost_millionth_usd": 3000000,
            "prompt_tokens": 10,
            "completion_tokens": 100,
            "reasoning_tokens": 100,
            "cached_tokens": 100,
        }
        _Trace.model_validate(payload)
