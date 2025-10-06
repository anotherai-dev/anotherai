import os
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import final

from pydantic import BaseModel, Field, ValidationError
from structlog import get_logger
from structlog.contextvars import bind_contextvars

from core.consts import ANOTHERAI_APP_URL
from core.domain.events import EventRouter, UserConnectedEvent
from core.domain.exceptions import InvalidTokenError, ObjectNotFoundError
from core.domain.tenant_data import TenantData, User
from core.services.user_manager import UserManager
from core.storage.tenant_storage import TenantStorage
from core.storage.user_storage import UserStorage
from core.utils.signature_verifier import SignatureVerifier

NO_AUTHORIZATION_ALLOWED = os.getenv("NO_AUTHORIZATION_ALLOWED") == "true"


_log = get_logger(__name__)


@final
class SecurityService:
    def __init__(
        self,
        tenant_storage: TenantStorage,
        verifier: SignatureVerifier,
        user_manager: UserManager,
        user_storage: UserStorage,
        event_router: EventRouter,
    ):
        self._tenant_storage = tenant_storage
        self._verifier = verifier
        self._user_manager = user_manager
        self._user_storage = user_storage
        self._event_router = event_router

    async def _no_tenant(self) -> TenantData:
        try:
            return await self._tenant_storage.tenant_by_owner_id("")
        except ObjectNotFoundError:
            return await self._tenant_storage.create_tenant(TenantData(slug="", owner_id=""))

    async def _api_key_tenant(self, token: str) -> TenantData:
        try:
            return await self._tenant_storage.tenant_by_api_key(token)
        except ObjectNotFoundError:
            raise InvalidTokenError.from_invalid_api_key(token) from None

    async def _tenant_from_org_id(self, org_id: str, claims: "_Claims") -> TenantData:
        try:
            return await self._tenant_storage.tenant_by_org_id(org_id)
        except ObjectNotFoundError:
            # org id is not found but we have a valid claims so we can create a new tenant
            return await self._registration(
                self._tenant_storage.create_tenant_for_org_id(org_id, claims.org_slug or org_id, claims.sub),
            )

    async def _tenant_from_owner_id(self, owner_id: str) -> TenantData:
        try:
            return await self._tenant_storage.tenant_by_owner_id(owner_id)
        except ObjectNotFoundError:
            # owner id is not found but we have a valid claims so we can create a new tenant
            return await self._registration(self._tenant_storage.create_tenant_for_owner_id(owner_id))

    async def _registration(self, coro: Awaitable[TenantData]):
        tenant = await coro
        # Check if tenant was just created, could be that it was migrated from a personal tenant to an organization
        if tenant.created_at and tenant.created_at > datetime.now(UTC) - timedelta(minutes=1):
            _log.info(
                "Tenant created",
                analytics="signup",
                tenant=tenant,
                org_id=tenant.org_id,
            )
        return tenant

    def token_from_header(self, authorization: str) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            # Shortcut to allow avoiding authentication alltogether
            # We basically create a tenant 0
            if NO_AUTHORIZATION_ALLOWED:
                return ""
            raise InvalidTokenError(
                "Authorization header is missing. "
                "A valid authorization header with an API key looks like 'Bearer aai-****'. If you need a new API key, "
                f"Grab a fresh one (plus $5 in free LLM credits for new users) at {ANOTHERAI_APP_URL}/keys 🚀",
            )
        return authorization.split(" ")[1]

    async def _oauth_tenant(self, token: str) -> TenantData:
        user_id = await self._user_manager.validate_oauth_token(token)
        try:
            data = await self._user_storage.last_used_organization(user_id)
        except ObjectNotFoundError:
            # If the user is not found, we auto create a tenant for the user
            data = await self._tenant_from_owner_id(user_id)
        data.user = User(sub=user_id, email=None)  # TODO: email
        return data

    async def _find_tenant(self, token: str) -> TenantData:
        if not token:
            # Shortcut to allow avoiding authentication alltogether
            # We basically create a tenant 0
            if NO_AUTHORIZATION_ALLOWED:
                return await self._no_tenant()
            raise InvalidTokenError(
                "Authorization header is missing. "
                "A valid authorization header with an API key looks like 'Bearer aai-****'. If you need a new API key, "
                f"Grab a fresh one (plus $5 in free LLM credits for new users) at {ANOTHERAI_APP_URL}/keys 🚀",
            )
        if is_api_key(token):
            return await self._api_key_tenant(token)

        if is_oauth_token(token):
            return await self._oauth_tenant(token)

        raw_claims = await self._verifier.verify(token)
        try:
            claims = _Claims.model_validate(raw_claims)
        except ValidationError as e:
            raise InvalidTokenError("Invalid token claims", capture=True) from e
        if claims.org_id:
            tenant = await self._tenant_from_org_id(claims.org_id, claims)
        else:
            tenant = await self._tenant_from_owner_id(claims.sub)
        tenant.user = User(
            sub=claims.sub,
            email=claims.email,
        )

        return tenant

    async def find_tenant(self, token: str) -> TenantData:
        tenant = await self._find_tenant(token)
        if tenant.user:
            self._event_router(UserConnectedEvent(user_id=tenant.user.sub, organization_id=tenant.org_id))
        bind_contextvars(
            tenant=tenant.slug,
            user_email=tenant.user.email if tenant.user else None,
        )
        return tenant


class _Claims(BaseModel):
    sub: str = Field(min_length=1)
    org_id: str | None = None
    org_slug: str | None = None
    email: str | None = None


def is_api_key(token: str) -> bool:
    return token.startswith("aai-")


def is_oauth_token(token: str) -> bool:
    return token.startswith("oat_")
