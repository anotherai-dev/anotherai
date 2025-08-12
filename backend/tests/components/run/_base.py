from abc import ABC, abstractmethod

from core.domain.models.models import Model
from core.domain.models.providers import Provider


class ProviderTestCase(ABC):
    @abstractmethod
    def provider(self) -> Provider:
        pass

    def __str__(self) -> str:
        return self.provider()

    @abstractmethod
    def model(self) -> Model:
        pass


class OpenAITestCase(ProviderTestCase):
    def provider(self) -> Provider:
        return Provider.OPEN_AI

    def model(self) -> Model:
        return Model.GPT_41_MINI_2025_04_14
