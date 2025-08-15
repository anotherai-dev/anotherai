from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from core.domain.models import Provider
from core.providers._base.abstract_provider import AbstractProvider
from core.providers._base.config import ProviderConfig


class AbstractProviderFactory(ABC):
    @abstractmethod
    def build_provider(
        self,
        config: ProviderConfig,
        config_id: str,
        preserve_credits: bool | None,
    ) -> AbstractProvider[Any, Any]:
        pass

    @abstractmethod
    def get_provider(self, provider: Provider) -> AbstractProvider[Any, Any]:
        pass

    @abstractmethod
    def get_providers(self, provider: Provider) -> Iterable[AbstractProvider[Any, Any]]:
        pass

    @abstractmethod
    def provider_type(self, provider: Provider) -> type[AbstractProvider[Any, Any]]:
        pass

    @abstractmethod
    def available_providers(self) -> Iterable[Provider]:
        pass
