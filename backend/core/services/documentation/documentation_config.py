import os
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, ValidationError
from structlog import get_logger

from core.consts import ENV_NAME

_log = get_logger(__name__)


class _DocEnv(StrEnum):
    LOCAL = "local"
    PROD = "production"
    STAGING = "staging"


# Documentation config contains variables by environment
class _DocumentationConfigFile(BaseModel):
    environments: dict[_DocEnv, dict[str, str]]
    default: dict[str, str]


class DocumentationConfig(NamedTuple):
    directory: Path
    variables: dict[str, str]


def _is_docs_dir(dir: Path) -> _DocumentationConfigFile | None:
    if not dir.exists() or not dir.is_dir():
        return None

    config_path = dir / "config.json"
    if not config_path.exists():
        return None

    with open(config_path) as f:
        try:
            return _DocumentationConfigFile.model_validate_json(f.read())
        except ValidationError as e:
            _log.error("Invalid documentation config", error=e)
            return None


def _default_docs_directory() -> tuple[Path, _DocumentationConfigFile]:
    current = Path(__file__).parent.parent
    for _ in range(5):
        doc_dir = current / "docs"
        config = _is_docs_dir(doc_dir)
        if config:
            return doc_dir, config
        current = current.parent

    raise ValueError("Docs directory not found")


def _default_docs_env() -> _DocEnv:
    alias = {
        "prod": _DocEnv.PROD,
    }
    env_str = os.getenv("ANOTHERAI_DOCS_ENV", ENV_NAME)
    env_str = alias.get(env_str, env_str)
    try:
        return _DocEnv(env_str)
    except ValueError:
        return _DocEnv.PROD


def default_docs_config() -> DocumentationConfig:
    directory, config = _default_docs_directory()
    env = _default_docs_env()
    env_variables = config.environments.get(env, {})
    final_variables = {**config.default, **env_variables}
    _log.info("Default documentation config", directory=directory, env=env, final_variables=final_variables)
    return DocumentationConfig(directory / "content" / "docs", final_variables)
