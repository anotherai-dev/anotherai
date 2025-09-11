import os
from typing import final

from structlog import get_logger

from core.domain.events import EventRouter
from core.providers._base.httpx_provider_base import HTTPXProviderBase
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.services.user_manager import UserManager
from core.storage.storage_builder import StorageBuilder
from core.utils.background import wait_for_background_tasks
from core.utils.signature_verifier import (
    JWKSetSignatureVerifier,
    JWKSignatureVerifier,
    NoopSignatureVerifier,
    SignatureVerifier,
)
from protocol._common._default_event_router import SystemEventRouter, TenantEventRouter
from protocol.api._services.security_service import SecurityService

_log = get_logger(__name__)


@final
class LifecycleDependencies:
    def __init__(
        self,
        storage_builder: StorageBuilder,
        provider_factory: AbstractProviderFactory,
        user_manager: UserManager,
    ):
        self.storage_builder = storage_builder
        self.provider_factory = provider_factory
        self._user_manager = user_manager
        self.security_service = SecurityService(
            self.storage_builder.tenants(-1),
            _default_verifier(),
            self._user_manager,
        )
        self._system_event_router = SystemEventRouter()

    async def close(self):
        # TODO: not great ownership here, the objects are passed as parameters but we are closing them here
        await self.storage_builder.close()
        await self._user_manager.close()

    def tenant_event_router(self, tenant_uid: int) -> EventRouter:
        return TenantEventRouter(tenant_uid, self._system_event_router)

    def system_event_router(self) -> EventRouter:
        return self._system_event_router

    shared: "LifecycleDependencies | None" = None


async def startup() -> LifecycleDependencies:
    if LifecycleDependencies.shared:
        # We already started
        return LifecycleDependencies.shared
    from core.providers.factory.local_provider_factory import LocalProviderFactory

    storage_builder = await _default_storage_builder()
    provider_factory = LocalProviderFactory()
    _ = provider_factory.build_available_providers()

    shared_dependencies = LifecycleDependencies(storage_builder, provider_factory, _default_user_manager())
    LifecycleDependencies.shared = shared_dependencies
    return shared_dependencies


async def shutdown(dependencies: LifecycleDependencies):
    await dependencies.close()
    await wait_for_background_tasks()
    await HTTPXProviderBase.close()


def _default_verifier() -> SignatureVerifier:
    if jwk_url := os.environ.get("JWKS_URL"):
        return JWKSetSignatureVerifier(jwk_url)
    if jwk := os.environ.get("JWK"):
        return JWKSignatureVerifier(jwk)
    _log.warning("No signature verifier configured, using noop")
    return NoopSignatureVerifier()


async def _default_storage_builder() -> StorageBuilder:
    from protocol._common._default_storage_builder import DefaultStorageBuilder

    return await DefaultStorageBuilder.create()


def _default_user_manager() -> UserManager:
    if clerk_secret := os.environ.get("CLERK_SECRET"):
        from core.services.clerk.clerk_user_manager import ClerkUserManager

        return ClerkUserManager(clerk_secret)
    _log.warning("No user manager configured, using noop")

    class NoopUserManager(UserManager):
        async def close(self):
            pass

        async def validate_oauth_token(self, token: str) -> str:
            raise NotImplementedError("NoopUserManager does not support oauth tokens")

    return NoopUserManager()
