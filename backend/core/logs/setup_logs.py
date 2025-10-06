import logging
import os
from collections.abc import Iterable
from typing import Any

import pydantic_core
import structlog
from structlog.types import Processor

from core.logs._pydantic_processor import pydantic_processor


def sentry_processor():
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return None

    from sentry_sdk import init as sentry_init
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    from core.logs._sentry_processor import SentryProcessor

    sentry_init(
        dsn=dsn,
        environment=os.environ.get("ENV_NAME", "local"),
        release=os.environ.get("SENTRY_RELEASE", "local"),
        enable_tracing=True,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        send_default_pii=False,
    )
    return SentryProcessor(event_level=logging.WARNING)


def posthog_processor():
    api_key = os.environ.get("POSTHOG_API_KEY")
    if not api_key:
        return None
    from core.logs._posthog_processor import PostHogProcessor

    return PostHogProcessor(api_key=api_key, host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"))


def _json_serializer(value: Any, indent: int | None = None, *args: Any, **kwargs: Any) -> str:
    return pydantic_core.to_json(value, fallback=str, indent=indent, exclude_none=True).decode()


def _renderer(json: bool | None = None):
    if (json is None and os.environ.get("JSON_LOGS") == "1") or json:
        return structlog.processors.JSONRenderer(serializer=_json_serializer)
    return structlog.dev.ConsoleRenderer()


def _processors(*extras: Processor) -> Iterable[Processor]:
    yield structlog.contextvars.merge_contextvars  # request-scoped context
    yield structlog.stdlib.add_log_level
    yield structlog.processors.TimeStamper(fmt="iso", utc=True)
    yield pydantic_processor

    if sentry := sentry_processor():
        yield sentry
    if posthog := posthog_processor():
        yield posthog
    yield from extras


def setup_logs(
    json: bool | None = None,
    *processors: Processor,
):
    min_level = os.getenv("LOG_LEVEL", "INFO")

    # Convert string level to logging constant
    numeric_level = getattr(logging, min_level.upper(), logging.INFO)

    structlog.configure(
        processors=list(_processors(*processors)),
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=True,
    )
