# pyright: reportPrivateUsage=false

from unittest.mock import Mock, patch

import pytest

from core.logs._posthog_processor import PostHogProcessor


@pytest.fixture
def mock_posthog():
    from posthog import Posthog

    mock = Mock(spec=Posthog)
    mock.capture = Mock()
    with patch("core.logs._posthog_processor.Posthog", return_value=mock):
        yield mock


@pytest.fixture
def processor(mock_posthog: Mock):
    return PostHogProcessor("test_api_key")


class TestBuildEventProperties:
    def test_build_event_properties_excludes_internal_keys(self, processor: PostHogProcessor):
        """Test that internal structlog keys are excluded from event properties."""

        event_dict = {
            "event": "test_event",
            "level": "info",
            "logger": "test_logger",
            "timestamp": "2023-01-01T00:00:00Z",
            "analytics": "test_analytics",
            "sentry": "test_sentry",
            "sentry_id": "123",
            "sentry_skip": True,
            "_internal_key": "should_be_excluded",
            "valid_key": "should_be_included",
            "another_valid": 42,
        }

        properties = processor._build_event_properties(event_dict)
        assert properties == {
            "valid_key": "should_be_included",
            "another_valid": 42,
            "env": "local",
        }


class TestSendAnalyticsEvent:
    @pytest.mark.parametrize(
        ("user_id", "tenant", "expected_user_id"),
        [
            ("user123", None, "user123"),
            (None, "tenant456", "tenant456"),
            ("user123", "tenant456", "user123"),  # user_id takes precedence
            (None, None, "anonymous"),
            ("", "", "anonymous"),  # Empty strings should fallback to anonymous
        ],
    )
    def test_user_id_detection(
        self,
        user_id: str | None,
        tenant: str | None,
        expected_user_id: str,
        mock_posthog: Mock,
        processor: PostHogProcessor,
    ):
        """Test user ID detection logic with various scenarios."""

        event_dict = {
            "analytics": "test_event",
            "some_data": "value",
        }

        if user_id is not None:
            event_dict["user_id"] = user_id
        if tenant is not None:
            event_dict["tenant"] = tenant

        processor._send_analytics_event(event_dict, "test_event")

        mock_posthog.capture.assert_called_once()
        call_args = mock_posthog.capture.call_args
        assert call_args[1]["distinct_id"] == expected_user_id

    def test_send_analytics_event_includes_timestamp(self, mock_posthog: Mock, processor: PostHogProcessor):
        """Test that timestamp is included in event properties."""

        event_dict = {
            "analytics": "test_event",
            "user_id": "test_user",
            "some_data": "value",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        processor._send_analytics_event(event_dict, "test_event")

        mock_posthog.capture.assert_called_once()
        call_args = mock_posthog.capture.call_args
        assert call_args[1]["timestamp"] == "2023-01-01T00:00:00Z"
        properties = call_args[1]["properties"]

        assert properties["some_data"] == "value"
        # Excluded keys should not be in properties
        assert "analytics" not in properties
        # user_id is not in _EXCLUDED_KEYS, so it should be included in properties
        assert properties["user_id"] == "test_user"

    def test_processor_does_not_removes_analytics_key(self, mock_posthog: Mock, processor: PostHogProcessor):
        """Test that analytics key is removed from event_dict after processing."""

        event_dict = {
            "analytics": "test_event",
            "user_id": "test_user",
            "some_data": "value",
        }

        result = processor(None, "test_logger", event_dict)
        mock_posthog.capture.assert_called_once()

        assert result == {
            "analytics": "test_event",
            "user_id": "test_user",
            "some_data": "value",
        }

    def test_processor_does_nothing_without_analytics_key(self, mock_posthog: Mock, processor: PostHogProcessor):
        """Test that processor does nothing when analytics key is not present."""

        event_dict = {
            "user_id": "test_user",
            "some_data": "value",
        }

        result = processor(None, "test_logger", event_dict)

        # No PostHog call should be made
        mock_posthog.capture.assert_not_called()
        # Event dict should be unchanged
        assert result == event_dict

    def test_processor_silences_posthog_errors(self, mock_posthog: Mock, processor: PostHogProcessor):
        """Test that PostHog errors are properly silenced using capture_errors."""

        event_dict = {
            "analytics": "test_event",
            "user_id": "test_user",
        }
        mock_posthog.capture.side_effect = Exception("PostHog error")

        result = processor(None, "test_logger", event_dict)
        assert result == event_dict

        mock_posthog.capture.assert_called_once()

    def test_processor_silences_build_properties_errors(self, mock_posthog: Mock, processor: PostHogProcessor):
        """Test that errors in _build_event_properties are silenced."""

        event_dict = {
            "analytics": "test_event",
            "user_id": "test_user",
        }

        # Make _build_event_properties raise an exception
        with patch.object(
            processor,
            "_build_event_properties",
            side_effect=Exception("Properties error"),
        ) as mock_build_event_properties:
            result = processor(None, "test_logger", event_dict)
            mock_build_event_properties.assert_called_once()

        assert result == {
            "analytics": "test_event",
            "user_id": "test_user",
        }

        mock_posthog.capture.assert_not_called()
