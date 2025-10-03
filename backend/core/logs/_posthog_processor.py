import contextlib
import os
from typing import Any

import posthog
from structlog.types import EventDict, WrappedLogger


class PostHogProcessor:
    """PostHog processor for structlog.

    Sends analytics events to PostHog when 'analytics' key is present in context.
    """

    def __init__(
        self,
        active: bool = True,
        verbose: bool = False,
    ) -> None:
        """
        :param active: A flag to make this processor enabled/disabled.
        :param verbose: Report the action taken by the logger in the `event_dict`.
            Default is :obj:`False`.
        """
        self.active = active
        self.verbose = verbose
        self._posthog_configured = False

        api_key = os.environ.get("POSTHOG_API_KEY")
        host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")

        if api_key:
            posthog.api_key = api_key
            posthog.host = host
            self._posthog_configured = True

    def _build_event_properties(self, event_dict: EventDict) -> dict[str, Any]:
        """Build event properties from structlog context.

        Excludes internal structlog keys and includes relevant context data.
        """
        excluded_keys = {
            "event",
            "level",
            "logger",
            "timestamp",
            "analytics",
            "sentry",
            "sentry_id",
            "sentry_skip",
        }

        properties: dict[str, Any] = {}
        for key, value in event_dict.items():
            if key not in excluded_keys and not key.startswith("_"):
                with contextlib.suppress(Exception):
                    properties[key] = value

        return properties

    def _send_analytics_event(self, event_dict: EventDict, event_name: str) -> None:
        """Send analytics event to PostHog."""
        with contextlib.suppress(Exception):
            user_id = event_dict.get("user_id") or event_dict.get("tenant_uid") or "anonymous"

            properties = self._build_event_properties(event_dict)

            properties["timestamp"] = event_dict.get("timestamp")

            posthog.capture(
                distinct_id=str(user_id),
                event=event_name,
                properties=properties,
            )

            if self.verbose:
                event_dict["posthog"] = "sent"

    def __call__(
        self,
        logger: WrappedLogger,
        name: str,
        event_dict: EventDict,
    ) -> EventDict:
        """A middleware to process structlog `event_dict` and send analytics to PostHog."""
        analytics_event = event_dict.pop("analytics", None)

        if self.active and self._posthog_configured and analytics_event:
            self._send_analytics_event(event_dict, analytics_event)
        elif self.verbose and analytics_event:
            event_dict.setdefault("posthog", "skipped" if not self._posthog_configured else "inactive")

        return event_dict
