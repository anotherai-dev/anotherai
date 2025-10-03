import os
from typing import Any

import posthog
from structlog.types import EventDict, WrappedLogger


class PostHogProcessor:
    def __init__(self, api_key: str | None = None, host: str | None = None, active: bool = True):
        self.active = active and api_key is not None
        if self.active:
            posthog.api_key = api_key
            posthog.host = host or "https://us.i.posthog.com"

    @classmethod
    def from_env(cls) -> "PostHogProcessor":
        return cls(
            api_key=os.getenv("POSTHOG_API_KEY"),
            host=os.getenv("POSTHOG_HOST"),
        )

    def __call__(
        self,
        logger: WrappedLogger,
        name: str,
        event_dict: EventDict,
    ) -> EventDict:
        if not self.active:
            return event_dict

        analytics_event = event_dict.pop("analytics", None)
        if not analytics_event:
            return event_dict

        distinct_id = event_dict.get("user_id") or event_dict.get("tenant_uid") or "anonymous"
        properties = self._build_properties(event_dict)

        posthog.capture(
            distinct_id=str(distinct_id),
            event=analytics_event,
            properties=properties,
        )

        return event_dict

    @staticmethod
    def _build_properties(event_dict: EventDict) -> dict[str, Any]:
        excluded_keys = {
            "event",
            "level",
            "logger",
            "timestamp",
            "sentry",
            "sentry_id",
            "sentry_skip",
        }
        return {k: v for k, v in event_dict.items() if k not in excluded_keys}
