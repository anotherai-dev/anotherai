from typing import Any

from posthog import Posthog
from structlog import get_logger
from structlog.types import EventDict, WrappedLogger

from core.utils.coroutines import capture_errors

_EXCLUDED_KEYS = {
    "event",
    "level",
    "logger",
    "timestamp",
    "analytics",
    "sentry",
    "sentry_id",
    "sentry_skip",
}


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

    def _build_event_properties(self, event_dict: EventDict) -> dict[str, Any]:
        """Build event properties from structlog context.

        Excludes internal structlog keys and includes relevant context data.
        """

        return {
            key: value for key, value in event_dict.items() if key not in _EXCLUDED_KEYS and not key.startswith("_")
        }

    def _send_analytics_event(self, event_dict: EventDict, event_name: str) -> None:
        """Send analytics event to PostHog."""
        user_id = event_dict.get("user_id") or event_dict.get("tenant") or "anonymous"

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

        if analytics_event := event_dict.get("analytics", None):
            with capture_errors(get_logger(__name__), f"Failed to send analytics event to PostHog: {analytics_event}"):
                self._send_analytics_event(event_dict, analytics_event)

        return event_dict
