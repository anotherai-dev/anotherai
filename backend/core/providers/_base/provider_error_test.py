from httpx import Request, Response

from core.domain.models import Provider
from core.providers._base.provider_error import ProviderError

from .provider_error import UnknownProviderError


def test_provider_error_init():
    error = ProviderError("Test error")
    assert str(error) == "Test error"
    assert error.status_code == 500
    assert error.retry is False
    assert error.capture is True


def test_provider_error_custom_status_code():
    error = ProviderError("Custom status", status_code=418)
    assert error.status_code == 418


def test_provider_error_with_response():
    """Check that the status code is properly set from the response when the
    default status code is None for the ProviderError"""
    response = Response(418, request=Request("GET", "https://example.com"))

    # Instantiating with the response
    error = ProviderError("Response error", response=response)
    assert error.status_code == 418
    assert error.provider_status_code == 418

    # Instantiating without the response and setting later
    error = ProviderError("Response error")
    error.set_response(response)
    assert error.status_code == 418
    assert error.provider_status_code == 418


def test_200_status_code_is_not_set():
    """When the provider returns a 200 status code but we still raise an error,
    we should not return a 200 status code"""
    response = Response(200, request=Request("GET", "https://example.com"))
    error = ProviderError("Response error", response=response)
    assert error.status_code == 500
    assert error.provider_status_code == 200


def test_provider_error_status_code_priority():
    response = Response(418, request=Request("GET", "https://example.com"))
    error = ProviderError("Priority test", status_code=400, response=response)
    assert error.status_code == 400  # Explicitly provided status_code should have priority


class TestUnknownProviderError:
    def test_default_fingerprint(self):
        error = UnknownProviderError("Test error", provider=Provider.GOOGLE)
        assert error.fingerprint == ["unknown_provider_error", Provider.GOOGLE.value, "Test error"]

    def test_default_fingerprint_with_provider_error(self):
        error = UnknownProviderError(
            "Test error",
            provider=Provider.GOOGLE,
            provider_error={"message": "Provider error"},
        )
        assert error.fingerprint == ["unknown_provider_error", Provider.GOOGLE.value, "{'message': 'Provider error'}"]
