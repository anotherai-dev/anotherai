import pytest
from pytest_httpx import HTTPXMock

from core.services.clerk.clerk_user_manager import ClerkUserManager


@pytest.fixture
def clerk_user_manager():
    return ClerkUserManager(secret_key="not_a_secret")  # noqa: S106


class TestValidateOAuthToken:
    async def test_validate_oauth_token(self, clerk_user_manager: ClerkUserManager, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.clerk.com/v1/oauth_applications/access_tokens/verify",
            json={
                "object": "clerk_idp_oauth_access_token",
                "id": "oat_0ef5a7a33d87ed87ee7954c845d80450",
                "client_id": "client_2xhFjEI5X2qWRvtV13BzSj8H6Dk",
                "subject": "user_2xhFjEI5X2qWRvtV13BzSj8H6Dk",
                "scopes": [
                    "read",
                    "write",
                ],
                "revoked": False,
                "revocation_reason": "Revoked by user",
                "expired": False,
                "expiration": 1716883200,
                "created_at": 1716883200,
                "updated_at": 1716883200,
            },
        )

        user_id = await clerk_user_manager.validate_oauth_token("test_token")
        assert user_id == "user_2xhFjEI5X2qWRvtV13BzSj8H6Dk"

        req = httpx_mock.get_request()
        assert req
        assert req.headers["Authorization"] == "Bearer not_a_secret"
