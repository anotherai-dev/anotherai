import os
from collections.abc import Callable
from typing import Any, Protocol, final

from structlog import get_logger

from core.domain.events import EventRouter
from core.domain.tenant_data import TenantData
from core.providers._base.httpx_provider_base import HTTPXProviderBase
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.services.email_service import EmailService
from core.services.payment_service import PaymentHandler
from core.services.user_manager import UserManager
from core.services.user_service import OrganizationDetails, UserDetails, UserService
from core.storage.kv_storage import KVStorage
from core.storage.storage_builder import StorageBuilder
from core.storage.tenant_storage import TenantStorage
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
        user_manager: "_UserHandler",
    ):
        self.storage_builder = storage_builder
        self.provider_factory = provider_factory
        self._user_manager = user_manager
        self._system_event_router = SystemEventRouter()
        self.security_service = SecurityService(
            self.storage_builder.tenants(-1),
            _default_verifier(),
            self._user_manager,
            user_storage=self.storage_builder.users(-1),
            event_router=self._system_event_router,
        )
        self._kv_storage = _default_kv_storage()
        from core.utils import remote_cached

        remote_cached.shared_cache = self._kv_storage
        self._email_service_builder = _default_email_service_builder()
        self._payment_handler_builder = _payment_handler_builder()

    async def close(self):
        # TODO: not great ownership here, the objects are passed as parameters but we are closing them here
        await self.storage_builder.close()
        await self._user_manager.close()
        await self._kv_storage.close()

    def tenant_event_router(self, tenant_uid: int) -> EventRouter:
        return TenantEventRouter(tenant_uid, self._system_event_router)

    def system_event_router(self) -> EventRouter:
        return self._system_event_router

    def email_service(self, tenant_uid: int) -> EmailService:
        return self._email_service_builder(self.storage_builder.tenants(tenant_uid), self._user_manager)

    def payment_handler(self, tenant_uid: int) -> PaymentHandler:
        return self._payment_handler_builder(
            self.storage_builder.tenants(tenant_uid),
            self.tenant_event_router(tenant_uid),
            self._email_service_builder(self.storage_builder.tenants(tenant_uid), self._user_manager),
        )

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


def _default_kv_storage() -> KVStorage:
    if "REDIS_DSN" in os.environ:
        from core.storage.redis.redis_storage import RedisStorage

        return RedisStorage(os.environ["REDIS_DSN"])
    _log.warning("No kv storage configured, using local")
    from core.storage.local_kv_storage.local_kv_storage import LocalKVStorage

    return LocalKVStorage()


async def _default_storage_builder() -> StorageBuilder:
    from protocol._common._default_storage_builder import DefaultStorageBuilder

    return await DefaultStorageBuilder.create()


class _UserHandler(UserManager, UserService, Protocol):
    pass


def _default_user_manager() -> _UserHandler:
    if clerk_secret := os.environ.get("CLERK_SECRET"):
        from core.services.clerk.clerk_user_manager import ClerkUserManager

        return ClerkUserManager(clerk_secret)
    _log.warning("No user manager configured, using noop")

    class NoopUserManager(_UserHandler):
        async def close(self):
            pass

        async def validate_oauth_token(self, token: str) -> str:
            raise NotImplementedError("NoopUserManager does not support oauth tokens")

        async def get_organization(self, org_id: str) -> OrganizationDetails:
            raise NotImplementedError("NoopUserManager does not support organizations")

        async def get_org_admins(self, org_id: str) -> list[UserDetails]:
            raise NotImplementedError("NoopUserManager does not support org admins")

        async def get_user(self, user_id: str) -> UserDetails:
            raise NotImplementedError("NoopUserManager does not support users")

    return NoopUserManager()


def _default_email_service_builder():
    if loops_api_key := os.environ.get("LOOPS_API_KEY"):
        from core.services.loops.loops_email_service import LoopsEmailService

        def _build(tenant_storage: TenantStorage, user_service: UserService):
            return LoopsEmailService(loops_api_key, tenant_storage, user_service)

        return _build
    _log.warning("No email service configured, using noop")

    class NoopEmailService(EmailService):
        async def send_payment_failure_email(self) -> None:
            _log.warning("NoopEmailService does not support payment failure emails")

        async def send_low_credits_email(self) -> None:
            _log.warning("NoopEmailService does not support low credits emails")

        @classmethod
        def build(cls, tenant_storage: TenantStorage, user_service: UserService):
            return cls()

    return NoopEmailService.build


def _payment_handler_builder() -> Callable[[TenantStorage, EventRouter, EmailService], PaymentHandler]:
    if "STRIPE_API_KEY" in os.environ:
        from core.services.stripe.stripe_service import StripeService

        def _build_stripe(tenant_storage: TenantStorage, event_router: EventRouter, email_service: EmailService):
            return StripeService(tenant_storage, event_router=event_router, email_service=email_service)

        return _build_stripe

    _log.warning("No payment handler configured, using noop")

    class NoopPaymentHandler(PaymentHandler):
        async def raise_for_negative_credits(self) -> None:
            _log.warning("NoopPaymentHandler does not support raise_for_negative_credits")

        async def handle_credit_decrement(self, tenant: TenantData) -> None:
            _log.warning("NoopPaymentHandler does not support handle_credit_decrement")

    def _build_noop(*args: Any, **kwargs: Any):
        return NoopPaymentHandler()

    return _build_noop
