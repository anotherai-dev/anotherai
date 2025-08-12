from pydantic import ValidationError

from core.providers.google.google_provider_domain import CompletionResponse, StreamedResponse
from tests.utils import fixture_bytes, fixtures_json


class TestCompletionResponse:
    def test_completion_response(self):
        payload = fixture_bytes("gemini", "response.json")
        raw = CompletionResponse.model_validate_json(payload)
        assert raw


class TestStreamedResponse:
    def test_streamed_response(self):
        payload = fixtures_json("gemini", "streamed_response.json")

        for i, chunk in enumerate(payload):
            try:
                raw = StreamedResponse.model_validate(chunk)
            except ValidationError as e:
                raise AssertionError(f"failed at index {i}") from e

            assert raw

    def test_with_safety_reason(self):
        payload = fixture_bytes("gemini", "with_safety_reason.json")
        try:
            StreamedResponse.model_validate_json(payload)
        except ValidationError as e:
            raise AssertionError("failed") from e

    def test_streamed_response_with_max_tokens(self):
        payload = fixture_bytes("gemini", "finish_reason_max_tokens_stream_completion.json")
        chunks = [chunk for chunk in payload if isinstance(chunk, dict)]

        for i, chunk in enumerate(chunks):
            try:
                raw = StreamedResponse.model_validate(chunk)
            except ValidationError as e:
                raise AssertionError(f"failed at index {i}") from e

            assert raw
