import pytest
from pytest_httpx import HTTPXMock

from core.services.clerk.clerk_user_manager import ClerkUserManager
from core.services.user_service import UserDetails


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


class TestGetUserEmail:
    async def test_get_user_email(self, clerk_user_manager: ClerkUserManager, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.clerk.com/v1/users/test_user_id",
            status_code=200,
            json={
                "id": "test_user_id",
                "primary_email_address_id": "email_1",
                "email_addresses": [
                    {"id": "email_1", "email_address": "primary@example.com"},
                    {"id": "email_2", "email_address": "secondary@example.com"},
                ],
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        # Execute
        result = await clerk_user_manager.get_user("test_user_id")

        # Verify
        assert isinstance(result, UserDetails)
        assert result.email == "primary@example.com"
        assert result.name == "John Doe"

        req = httpx_mock.get_requests()
        assert len(req) == 1
        assert req[0].url == "https://api.clerk.com/v1/users/test_user_id"
        assert req[0].headers["Authorization"] == "Bearer test_secret"

    async def test_get_user_email_with_no_primary_email(
        self,
        clerk_user_manager: ClerkUserManager,
        httpx_mock: HTTPXMock,
    ):
        httpx_mock.add_response(
            url="https://api.clerk.com/v1/users/test_user_id",
            status_code=200,
            json={
                "id": "test_user_id",
                "email_addresses": [
                    {"id": "email_2", "email_address": "secondary@example.com"},
                ],
            },
        )

        # Execute
        result = await clerk_user_manager.get_user("test_user_id")

        # Verify
        assert isinstance(result, UserDetails)
        assert result.email == "secondary@example.com"

    async def test_get_user_email_with_primary_email_missing(
        self,
        clerk_user_manager: ClerkUserManager,
        httpx_mock: HTTPXMock,
    ):
        httpx_mock.add_response(
            url="https://api.clerk.com/v1/users/test_user_id",
            status_code=200,
            json={
                "id": "test_user_id",
                "primary_email_address_id": "blabla",
                "email_addresses": [
                    {"id": "email_2", "email_address": "secondary@example.com"},
                ],
            },
        )

        # Execute
        result = await clerk_user_manager.get_user("test_user_id")

        # Verify
        assert isinstance(result, UserDetails)
        assert result.email == "secondary@example.com"


class TestGetUsersById:
    async def test_get_users_by_id(self, clerk_user_manager: ClerkUserManager, httpx_mock: HTTPXMock):
        user_ids = ["user1", "user2"]
        httpx_mock.add_response(
            url="https://api.clerk.com/v1/users?user_ids=user1,user2",
            status_code=200,
            json=[
                {
                    "id": "user1",
                    "primary_email_address_id": "email1",
                    "email_addresses": [
                        {"id": "email1", "email_address": "user1@example.com"},
                    ],
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "id": "user2",
                    "primary_email_address_id": "email2",
                    "email_addresses": [
                        {"id": "email2", "email_address": "user2@example.com"},
                    ],
                    "first_name": "User",
                    "last_name": "Two",
                },
            ],
        )

        result = await clerk_user_manager._get_users_by_id(user_ids)  # pyright: ignore [reportPrivateUsage]

        assert len(result) == 2
        assert result[0].email == "user1@example.com"
        assert result[0].name == "User One"
        assert result[1].email == "user2@example.com"
        assert result[1].name == "User Two"


class TestGetOrgAdminIds:
    async def test_get_org_admin_ids(self, clerk_user_manager: ClerkUserManager, httpx_mock: HTTPXMock):
        org_id = "test_org"
        max_users = 5
        httpx_mock.add_response(
            url=f"https://api.clerk.com/v1/organizations/{org_id}/memberships?role=org:admin&limit={max_users}",
            status_code=200,
            json={
                "data": [
                    {
                        "public_user_data": {"user_id": "admin1"},
                    },
                    {
                        "public_user_data": {"user_id": "admin2"},
                    },
                ],
                "total_count": 2,
            },
        )

        result = await clerk_user_manager._get_org_admin_ids(org_id, max_users)  # pyright: ignore [reportPrivateUsage]

        assert result == ["admin1", "admin2"]


class TestGetOrgAdmins:
    async def test_get_org_admins(self, clerk_user_manager: ClerkUserManager, httpx_mock: HTTPXMock):
        org_id = "test_org"
        max_users = 5

        # Mock the organization memberships response
        httpx_mock.add_response(
            url=f"https://api.clerk.com/v1/organizations/{org_id}/memberships?role=org:admin&limit={max_users}",
            status_code=200,
            json={
                "data": [
                    {
                        "public_user_data": {"user_id": "admin1"},
                    },
                    {
                        "public_user_data": {"user_id": "admin2"},
                    },
                ],
                "total_count": 2,
            },
        )

        # Mock the users response
        httpx_mock.add_response(
            url="https://api.clerk.com/v1/users?user_ids=admin1,admin2",
            status_code=200,
            json=[
                {
                    "id": "admin1",
                    "primary_email_address_id": "email1",
                    "email_addresses": [
                        {"id": "email1", "email_address": "admin1@example.com"},
                    ],
                    "first_name": "Admin",
                    "last_name": "One",
                },
                {
                    "id": "admin2",
                    "primary_email_address_id": "email2",
                    "email_addresses": [
                        {"id": "email2", "email_address": "admin2@example.com"},
                    ],
                    "first_name": "Admin",
                    "last_name": "Two",
                },
            ],
        )

        result = await clerk_user_manager.get_org_admins(org_id, max_users)

        assert len(result) == 2
        assert result[0].email == "admin1@example.com"
        assert result[0].name == "Admin One"
        assert result[1].email == "admin2@example.com"
        assert result[1].name == "Admin Two"
