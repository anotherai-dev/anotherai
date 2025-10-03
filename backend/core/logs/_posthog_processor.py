import logging
import os
from typing import Any

from posthog import Posthog
from structlog.types import EventDict, WrappedLogger


# Define at module level as requested
class PosthogMissing(Exception):
    """Raised when PostHog SDK is not available."""
    pass


class PostHogProcessor:
    """PostHog processor for structlog.

    Sends analytics events to PostHog when 'analytics' key is present in context.
    """

    def __init__(self, api_key: str, host: str = "https://us.i.posthog.com") -> None:
        """
        Initialize PostHog processor with API credentials.

        :param api_key: PostHog API key
        :param host: PostHog host URL, defaults to US cloud instance
        """
        self._posthog = Posthog(api_key, host=host)
        self._logger = logging.getLogger(__name__)

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
                try:
                    properties[key] = value
                except Exception:
                    # Skip values that can't be serialized
                    pass

        return properties

    def _send_analytics_event(self, event_dict: EventDict, event_name: str) -> None:
        """Send analytics event to PostHog."""
        user_id = event_dict.get("user_id") or event_dict.get("tenant_uid") or "anonymous"

        properties = self._build_event_properties(event_dict)
        properties["timestamp"] = event_dict.get("timestamp")

        self._posthog.capture(
            distinct_id=str(user_id),
            event=event_name,
            properties=properties,
        )

    def __call__(
        self,
        logger: WrappedLogger,
        name: str,
        event_dict: EventDict,
    ) -> EventDict:
        """A middleware to process structlog `event_dict` and send analytics to PostHog."""
        analytics_event = event_dict.pop("analytics", None)

        if analytics_event:
            try:
                self._send_analytics_event(event_dict, analytics_event)
            except Exception as e:
                # Log the exception but don't fail the logging pipeline
                self._logger.exception(f"Failed to send analytics event to PostHog: {e}")

        return event_dict