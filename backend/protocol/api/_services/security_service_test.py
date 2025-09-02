# ruff: noqa: S105

from unittest.mock import Mock, patch

import pytest

from core.domain.exceptions import InvalidTokenError, ObjectNotFoundError
from core.domain.tenant_data import TenantData
from core.storage.tenant_storage import TenantStorage
from core.utils.signature_verifier import SignatureVerifier
from protocol.api._services.security_service import SecurityService


@pytest.fixture
def mock_verifier():
    return Mock(spec=SignatureVerifier)


@pytest.fixture
def mock_tenant_storage():
    storage = Mock(spec=TenantStorage)
    return storage


@pytest.fixture
def security_service(mock_verifier: Mock, mock_tenant_storage: Mock):
    return SecurityService(tenant_storage=mock_tenant_storage, verifier=mock_verifier)


@pytest.fixture
def sample_tenant():
    return TenantData(uid=123, slug="test-tenant")


class TestFindTenant:
    async def test_no_auth_tenant_not_allowed(self, security_service: SecurityService, mock_tenant_storage: Mock):
        with pytest.raises(InvalidTokenError):
            _ = await security_service.find_tenant("")

        mock_tenant_storage.create_tenant.assert_not_called()

    @patch("protocol.api._services.security_service.NO_AUTHORIZATION_ALLOWED", True)
    async def test_no_auth_tenant_allowed_existing_tenant(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        mock_tenant_storage.tenant_by_owner_id.return_value = sample_tenant

        result = await security_service.find_tenant("")

        assert result == sample_tenant
        mock_tenant_storage.tenant_by_owner_id.assert_called_once_with("")
        mock_tenant_storage.create_tenant.assert_not_called()

    @patch("protocol.api._services.security_service.NO_AUTHORIZATION_ALLOWED", False)
    async def test_no_auth_tenant_not_allowed_existing_tenant(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        with pytest.raises(InvalidTokenError):
            await security_service.find_tenant("")

        mock_tenant_storage.tenant_by_owner_id.assert_not_called()

    @patch("protocol.api._services.security_service.NO_AUTHORIZATION_ALLOWED", True)
    async def test_no_auth_tenant_allowed_create_new_tenant(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        mock_tenant_storage.tenant_by_owner_id.side_effect = ObjectNotFoundError("tenant")
        mock_tenant_storage.create_tenant.return_value = sample_tenant

        result = await security_service.find_tenant("")

        assert result == sample_tenant
        mock_tenant_storage.tenant_by_owner_id.assert_called_once_with("")
        mock_tenant_storage.create_tenant.assert_called_once()
        # Check that create_tenant was called with correct TenantData
        created_tenant = mock_tenant_storage.create_tenant.call_args[0][0]
        assert created_tenant.uid == 0
        assert created_tenant.slug == ""

    async def test_none_authorization_tenant_not_allowed(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
    ):
        with pytest.raises(InvalidTokenError):
            _ = await security_service.find_tenant("")  # Use empty string instead of None

        mock_tenant_storage.tenant_by_owner_id.assert_not_called()

    async def test_invalid_bearer_format_tenant_not_allowed(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
    ):
        with pytest.raises(InvalidTokenError):
            _ = await security_service.find_tenant("Invalid format")

        mock_tenant_storage.tenant_by_owner_id.assert_not_called()

    async def test_invalid_bearer_format_tenant_allowed(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        mock_tenant_storage.tenant_by_owner_id.return_value = sample_tenant

        with pytest.raises(InvalidTokenError):
            await security_service.find_tenant("Invalid format")

        mock_tenant_storage.tenant_by_owner_id.assert_not_called()

    async def test_api_key_valid(
        self,
        security_service: SecurityService,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        api_key = "aai-test-key-123"
        mock_tenant_storage.tenant_by_api_key.return_value = sample_tenant

        result = await security_service.find_tenant(api_key)

        assert result == sample_tenant
        mock_tenant_storage.tenant_by_api_key.assert_called_once_with(api_key)

    async def test_api_key_invalid(self, security_service: SecurityService, mock_tenant_storage: Mock):
        api_key = "aai-invalid-key"
        mock_tenant_storage.tenant_by_api_key.side_effect = ObjectNotFoundError("tenant")

        with pytest.raises(InvalidTokenError):
            await security_service.find_tenant(api_key)

        mock_tenant_storage.tenant_by_api_key.assert_called_once_with(api_key)

    async def test_jwt_token_with_org_id_existing(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        token = "jwt-token-123"
        claims = {"sub": "user123", "org_id": "org456", "org_slug": "test-org"}
        mock_verifier.verify.return_value = claims
        mock_tenant_storage.tenant_by_org_id.return_value = sample_tenant

        result = await security_service.find_tenant(token)

        assert result == sample_tenant
        mock_verifier.verify.assert_called_once_with(token)
        mock_tenant_storage.tenant_by_org_id.assert_called_once_with("org456")
        mock_tenant_storage.create_tenant_for_org_id.assert_not_called()

    async def test_jwt_token_with_org_id_create_new(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        token = "jwt-token-123"
        claims = {"sub": "user123", "org_id": "org456", "org_slug": "test-org"}
        mock_verifier.verify.return_value = claims
        mock_tenant_storage.tenant_by_org_id.side_effect = ObjectNotFoundError("tenant")
        mock_tenant_storage.create_tenant_for_org_id.return_value = sample_tenant

        result = await security_service.find_tenant(token)

        assert result == sample_tenant
        mock_verifier.verify.assert_called_once_with(token)
        mock_tenant_storage.tenant_by_org_id.assert_called_once_with("org456")
        mock_tenant_storage.create_tenant_for_org_id.assert_called_once_with("org456", "test-org", "user123")

    async def test_jwt_token_with_org_id_no_slug(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        token = "jwt-token-123"
        claims = {"sub": "user123", "org_id": "org456"}  # No org_slug
        mock_verifier.verify.return_value = claims
        mock_tenant_storage.tenant_by_org_id.side_effect = ObjectNotFoundError("tenant")
        mock_tenant_storage.create_tenant_for_org_id.return_value = sample_tenant

        result = await security_service.find_tenant(token)

        assert result == sample_tenant
        # Should use org_id as fallback when org_slug is None
        mock_tenant_storage.create_tenant_for_org_id.assert_called_once_with("org456", "org456", "user123")

    async def test_jwt_token_without_org_id_existing(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        token = "jwt-token-123"
        claims = {"sub": "user123"}  # No org_id
        mock_verifier.verify.return_value = claims
        mock_tenant_storage.tenant_by_owner_id.return_value = sample_tenant

        result = await security_service.find_tenant(token)

        assert result == sample_tenant
        mock_verifier.verify.assert_called_once_with(token)
        mock_tenant_storage.tenant_by_owner_id.assert_called_once_with("user123")
        mock_tenant_storage.create_tenant_for_owner_id.assert_not_called()

    async def test_jwt_token_without_org_id_create_new(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
        sample_tenant: TenantData,
    ):
        token = "jwt-token-123"
        claims = {"sub": "user123"}  # No org_id
        mock_verifier.verify.return_value = claims
        mock_tenant_storage.tenant_by_owner_id.side_effect = ObjectNotFoundError("tenant")
        mock_tenant_storage.create_tenant_for_owner_id.return_value = sample_tenant

        result = await security_service.find_tenant(token)

        assert result == sample_tenant
        mock_verifier.verify.assert_called_once_with(token)
        mock_tenant_storage.tenant_by_owner_id.assert_called_once_with("user123")
        mock_tenant_storage.create_tenant_for_owner_id.assert_called_once_with("user123")

    async def test_jwt_token_invalid_signature(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
    ):
        token = "invalid-jwt-token"
        mock_verifier.verify.side_effect = Exception("Invalid signature")

        with pytest.raises(Exception, match="Invalid signature"):
            _ = await security_service.find_tenant(token)

        mock_verifier.verify.assert_called_once_with(token)
        # No storage methods should be called
        mock_tenant_storage.tenant_by_org_id.assert_not_called()
        mock_tenant_storage.tenant_by_owner_id.assert_not_called()

    async def test_jwt_token_invalid_claims_missing_sub(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
    ):
        token = "jwt-token-123"
        claims = {"org_id": "org456"}  # Missing required 'sub' field
        mock_verifier.verify.return_value = claims

        with pytest.raises(InvalidTokenError, match="Invalid token claims"):
            _ = await security_service.find_tenant(token)

        mock_verifier.verify.assert_called_once_with(token)
        # No storage methods should be called
        mock_tenant_storage.tenant_by_org_id.assert_not_called()
        mock_tenant_storage.tenant_by_owner_id.assert_not_called()

    async def test_jwt_token_invalid_claims_empty_sub(
        self,
        security_service: SecurityService,
        mock_verifier: Mock,
        mock_tenant_storage: Mock,
    ):
        token = "jwt-token-123"
        claims = {"sub": ""}  # Empty sub field (should fail validation with ge=1)
        mock_verifier.verify.return_value = claims

        with pytest.raises(InvalidTokenError, match="Invalid token claims"):
            _ = await security_service.find_tenant(token)

        mock_verifier.verify.assert_called_once_with(token)
        # No storage methods should be called
        mock_tenant_storage.tenant_by_org_id.assert_not_called()
        mock_tenant_storage.tenant_by_owner_id.assert_not_called()


class TestTokenFromHeader:
    @pytest.mark.parametrize("authorization", ["Basic blabla", "blabla"])
    def test_invalid_tokens(self, security_service: SecurityService, authorization: str):
        with pytest.raises(InvalidTokenError):
            security_service.token_from_header(authorization)

    @patch("protocol.api._services.security_service.NO_AUTHORIZATION_ALLOWED", True)
    @pytest.mark.parametrize("authorization", ["Bearer ", "Bearer", ""])
    def test_empty_tokens(self, security_service: SecurityService, authorization: str):
        result = security_service.token_from_header(authorization)

        assert result == ""

    @patch("protocol.api._services.security_service.NO_AUTHORIZATION_ALLOWED", False)
    @pytest.mark.parametrize("authorization", ["Bearer", ""])
    def test_empty_tokens_raises_if_not_allowed(self, security_service: SecurityService, authorization: str):
        with pytest.raises(InvalidTokenError):
            security_service.token_from_header(authorization)

    @pytest.mark.parametrize(
        ("authorization", "expected_token"),
        [
            ("Bearer token123", "token123"),
            ("Bearer aai-test-key", "aai-test-key"),
            ("Bearer jwt.token.here", "jwt.token.here"),
            ("Bearer token with spaces", "token"),  # Split on space, so only first part after Bearer
            ("Bearer token123 extra", "token123"),  # Only takes first token part
        ],
    )
    def test_various_valid_bearer_formats(
        self,
        security_service: SecurityService,
        authorization: str,
        expected_token: str,
    ):
        """Test various valid Bearer authorization formats."""
        result = security_service.token_from_header(authorization)

        assert result == expected_token
