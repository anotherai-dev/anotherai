from difflib import get_close_matches

import structlog

from core.agents.suggest_model import suggest_model as suggest_model_agent
from core.domain.models.models import Model

_log = structlog.get_logger(__name__)


async def suggest_model(model: str, deployments: list[str]) -> Model | None:
    try:
        suggested_model = await suggest_model_agent(model, [*list(Model), *deployments])
        return Model(suggested_model)
    except Exception:  # noqa: BLE001
        _log.exception(
            "Error suggesting model",
            model=model,
        )

    suggestion = get_close_matches(model, list(Model), n=1, cutoff=0.5)
    if not suggestion:
        _log.warning(
            "No similar model found for {model}",
            model=model,
        )
        return None
    return Model(suggestion[0])
