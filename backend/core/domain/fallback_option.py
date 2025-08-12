from typing import Literal

from core.domain.models.models import Model

type FallbackOption = Literal["auto", "never"] | list[Model] | None
