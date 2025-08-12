from unittest import mock

import pytest
from google.oauth2.service_account import Credentials

from core.providers.google.google_provider_auth import get_token


@pytest.fixture
def mock_from_service_account_info():
    with mock.patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        spec=Credentials.from_service_account_info,  # pyright: ignore [reportUnknownArgumentType]
    ) as mock_auth:
        yield mock_auth


class TestGetToken:
    async def test_get_token(self, mock_from_service_account_info: mock.Mock):
        mock_credentials = mock.Mock(spec=Credentials)
        mock_credentials.token = "token"  # noqa: S105
        # First call to get_token should create the credentials
        mock_from_service_account_info.return_value = mock_credentials

        token = await get_token("{}")
        assert token == "token"  # noqa: S105

        mock_from_service_account_info.assert_called_once()
        mock_credentials.refresh.assert_called_once()

        # Now we try again
        mock_credentials.valid = True
        token = await get_token("{}")

        mock_from_service_account_info.reset_mock()
        mock_credentials.reset_mock()

        mock_from_service_account_info.assert_not_called()
        mock_credentials.refresh.assert_not_called()
        assert token == "token"  # noqa: S105

        mock_from_service_account_info.reset_mock()
        mock_credentials.reset_mock()

        # Now the token is invalid
        mock_credentials.valid = False
        token = await get_token("{}")

        mock_from_service_account_info.assert_not_called()
        mock_credentials.refresh.assert_called_once()
        assert token == "token"  # noqa: S105
