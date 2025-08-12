import os
from typing import final

from pydantic import BaseModel, Field, ValidationError

from core.consts import ANOTHERAI_APP_URL
from core.domain.exceptions import InvalidTokenError, ObjectNotFoundError
from core.domain.tenant_data import TenantData
from core.storage.tenant_storage import TenantStorage
from core.utils.signature_verifier import SignatureVerifier


@final
class SecurityService:
    def __init__(self, tenant_storage: TenantStorage, verifier: SignatureVerifier):
        self._tenant_storage = tenant_storage
        self._verifier = verifier

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
            return await self._tenant_storage.create_tenant_for_org_id(org_id, claims.org_slug or org_id, claims.sub)

    async def _tenant_from_owner_id(self, owner_id: str) -> TenantData:
        try:
            return await self._tenant_storage.tenant_by_owner_id(owner_id)
        except ObjectNotFoundError:
            # owner id is not found but we have a valid claims so we can create a new tenant
            return await self._tenant_storage.create_tenant_for_owner_id(owner_id)

    async def find_tenant(self, authorization: str) -> TenantData:
        if not authorization or not authorization.startswith("Bearer "):
            # Shortcut to allow avoiding authentication alltogether
            # We basically create a tenant 0
            # TODO: change to remove default
            if os.getenv("NO_TENANT_ALLOWED", "true") == "true":
                return await self._no_tenant()
            raise InvalidTokenError(
                "Authorization header is missing. "
                "A valid authorization header with an API key looks like 'Bearer wai-****'. If you need a new API key, "
                f"Grab a fresh one (plus $5 in free LLM credits for new users) at {ANOTHERAI_APP_URL}/keys 🚀",
            )
        token = authorization.split(" ")[1]
        if is_api_key(token):
            return await self._api_key_tenant(token)

        raw_claims = await self._verifier.verify(token)
        try:
            claims = _Claims.model_validate(raw_claims)
        except ValidationError as e:
            raise InvalidTokenError("Invalid token claims", capture=True) from e
        if claims.org_id:
            return await self._tenant_from_org_id(claims.org_id, claims)
        return await self._tenant_from_owner_id(claims.sub)


class _Claims(BaseModel):
    sub: str = Field(min_length=1)
    org_id: str | None = None
    org_slug: str | None = None


def is_api_key(token: str) -> bool:
    return token.startswith("aai-")
