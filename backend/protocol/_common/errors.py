from contextlib import contextmanager
from typing import Any

from sentry_sdk import new_scope

from core.domain.exceptions import ScopeConfigurableError


@contextmanager
def configure_scope_for_error(
    error: BaseException,
    tags: dict[str, str | bool | int | float] | None = None,
    extras: dict[str, Any] | None = None,
):
    with new_scope() as scope:
        if tags:
            for k, v in tags.items():
                scope.set_tag(k, v)

        if extras:
            for k, v in extras.items():
                scope.set_extra(k, v)

        if isinstance(error, ScopeConfigurableError):
            error.configure_scope(scope)

        yield
