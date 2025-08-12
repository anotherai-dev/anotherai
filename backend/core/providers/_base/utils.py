import os
from typing import Any, NamedTuple

from core.domain.exceptions import MissingEnvVariablesError
from core.domain.models.model_data import ModelData
from core.domain.models.models import Model
from core.providers._base.provider_options import ProviderOptions
from core.utils.hash import hash_object
from core.utils.strings import slugify


def get_provider_config_env(key: str, index: int, default: str | None = None):
    """Retrieve a value for a given env. If no default is provided
    raises a MissingEnvVariablesError error"""
    env_var = f"{key}_{index}" if index > 0 else key
    if default:
        return os.environ.get(env_var, default)
    try:
        return os.environ[env_var]
    except KeyError:
        raise MissingEnvVariablesError([env_var]) from None


def should_use_structured_output(options: ProviderOptions, model_data: ModelData) -> bool:
    if options.structured_generation is False:
        return False

    return model_data.supports_structured_output


_MAX_SCHEMA_NAME_CHARACTERS_LENGTH = 60


def get_unique_schema_name(task_name: str | None, schema: dict[str, Any]) -> str:
    """Return a unique schema name truncated to 60 characters using the task name and schema hash."""
    # We want to limit the length of the schema name to 60 characters as OpenAI has a limit of 64 characters for the schema name
    # We keep a buffer of 4 character.

    # We don't know for sure what are the inner workings of the feature at OpenAI,
    # but passing a schema_name which is unique to the schema appeared safer, hence the hash.
    hash_str = hash_object(schema)
    snake_case_name = slugify(task_name).replace("-", "_") if task_name else ""
    # Reserve 32 chars for hash and 1 for underscore
    max_name_length = _MAX_SCHEMA_NAME_CHARACTERS_LENGTH - len(hash_str) - 1
    if len(snake_case_name) > max_name_length:
        snake_case_name = snake_case_name[:max_name_length]
    return f"{snake_case_name}_{hash_str}"


class ThinkingModelPair(NamedTuple):
    model: str
    reasoning_effort: str


type ThinkingModelMap = dict[Model, ThinkingModelPair]
