import logging
import os
from typing import Any

import pydantic_core
import structlog
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from structlog.types import Processor

from core.logs._posthog_processor import PostHogProcessor
from core.logs._pydantic_processor import pydantic_processor
from core.logs._sentry_processor import SentryProcessor


def setup_sentry():
    if os.environ.get("SENTRY_DSN"):
        sentry_init(
            dsn=os.environ.get("SENTRY_DSN"),
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


def _json_serializer(value: Any, indent: int | None = None, *args: Any, **kwargs: Any) -> str:
    return pydantic_core.to_json(value, fallback=str, indent=indent, exclude_none=True).decode()


def _renderer(json: bool | None = None):
    if (json is None and os.environ.get("JSON_LOGS") == "1") or json:
        return structlog.processors.JSONRenderer(serializer=_json_serializer)
    return structlog.dev.ConsoleRenderer()


def setup_logs(
    json: bool | None = None,
    *processors: Processor,
):
    setup_sentry()

    min_level = os.getenv("LOG_LEVEL", "INFO")

    # Convert string level to logging constant
    numeric_level = getattr(logging, min_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # request-scoped context
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            pydantic_processor,
            PostHogProcessor(),  # send analytics events to PostHog
            SentryProcessor(event_level=logging.WARNING),  # capture warnings+ as events
            _renderer(),
            *processors,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=True,
    )
