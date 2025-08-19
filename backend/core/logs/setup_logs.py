import logging
import os
from collections.abc import Callable

import structlog
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from structlog.types import Processor, WrappedLogger

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


def _renderer(json: bool | None = None):
    if (json is None and os.environ.get("JSON_LOGS") == "1") or json:
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer()


def setup_logs(
    logger_factory: Callable[[], "WrappedLogger"] | None = None,
    json: bool | None = None,
    *processors: Processor,
):
    setup_sentry()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # request-scoped context
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            pydantic_processor,
            SentryProcessor(event_level=logging.WARNING),  # capture warnings+ as events
            _renderer(),
            *processors,
        ],
        logger_factory=logger_factory or structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
