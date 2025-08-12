from collections.abc import Iterator
from typing import cast

from core.domain.models.model_data import FinalModelData, LatestModel
from core.domain.models.model_data_mapping import MODEL_DATAS
from core.domain.models.models import Model as ModelID
from protocol.api._api_models import Model
from protocol.api._services.conversions import model_response_from_domain


def _model_data_iterator() -> Iterator[Model]:
    for model in ModelID:
        data = MODEL_DATAS[model]
        final_data: FinalModelData | LatestModel
        if isinstance(data, LatestModel):
            final_data = cast(FinalModelData, MODEL_DATAS[data.model])
        elif isinstance(data, FinalModelData):
            final_data = data
        else:
            # Skipping deprecated models
            continue
        if not final_data.providers:
            continue
        yield model_response_from_domain(model.value, final_data)


async def list_models() -> list[Model]:
    return list(_model_data_iterator())
