import os
from typing import final

from structlog import get_logger

from core.providers._base.httpx_provider_base import HTTPXProviderBase
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.storage.storage_builder import StorageBuilder
from core.utils.background import wait_for_background_tasks
from core.utils.signature_verifier import (
    JWKSetSignatureVerifier,
    JWKSignatureVerifier,
    NoopSignatureVerifier,
    SignatureVerifier,
)
from protocol.api._services.security_service import SecurityService

_log = get_logger(__name__)


@final
class LifecycleDependencies:
    def __init__(self, storage_builder: StorageBuilder, provider_factory: AbstractProviderFactory):
        self.storage_builder = storage_builder
        self.provider_factory = provider_factory
        self.security_service = SecurityService(self.storage_builder.tenants(-1), _default_verifier())

    async def close(self):
        await self.storage_builder.close()

    shared: "LifecycleDependencies | None" = None


async def startup() -> LifecycleDependencies:
    if LifecycleDependencies.shared:
        # We already started
        return LifecycleDependencies.shared
    from core.providers.factory.local_provider_factory import LocalProviderFactory

    storage_builder = await _default_storage_builder()
    provider_factory = LocalProviderFactory()
    _ = provider_factory.build_available_providers()

    shared_dependencies = LifecycleDependencies(storage_builder, provider_factory)
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
    from core.storage._default_storage_builder import DefaultStorageBuilder

    return await DefaultStorageBuilder.create()
