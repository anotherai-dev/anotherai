# pyright: reportPrivateUsage=false

import pytest

from core.domain.annotation import Annotation
from core.storage.clickhouse._models._ch_annotation import ClickhouseAnnotation, _extract_metric
from core.utils.uuid import uuid7
from tests.fake_models import fake_annotation


class TestExtractMetric:
    def test_extract_metric_with_none(self):
        """Test that None metric returns all None values."""
        result = _extract_metric(None)
        assert result == (None, None, None, None)

    @pytest.mark.parametrize(
        ("metric_value", "expected"),
        [
            (3.14, ("accuracy", 3.14, None, None)),
            (0.0, ("score", 0.0, None, None)),
            (-1.5, ("deviation", -1.5, None, None)),
            (100.0, ("percentage", 100.0, None, None)),
        ],
    )
    def test_extract_metric_with_float_values(self, metric_value, expected):
        """Test that float metric values are extracted correctly."""
        metric = Annotation.Metric(name=expected[0], value=metric_value)
        result = _extract_metric(metric)
        assert result == expected

    @pytest.mark.parametrize(
        ("metric_value", "expected"),
        [
            ("excellent", ("quality", None, "excellent", None)),
            ("", ("empty", None, "", None)),
            ("123", ("number_str", None, "123", None)),
            ("user_feedback", ("type", None, "user_feedback", None)),
        ],
    )
    def test_extract_metric_with_string_values(self, metric_value, expected):
        """Test that string metric values are extracted correctly."""
        metric = Annotation.Metric(name=expected[0], value=metric_value)
        result = _extract_metric(metric)
        assert result == expected

    @pytest.mark.parametrize(
        ("metric_value", "expected"),
        [
            (True, ("is_valid", None, None, True)),
            (False, ("is_error", None, None, False)),
        ],
    )
    def test_extract_metric_with_bool_values(self, metric_value, expected):
        """Test that boolean metric values are extracted correctly."""
        metric = Annotation.Metric(name=expected[0], value=metric_value)
        result = _extract_metric(metric)
        assert result == expected


class TestFromDomain:
    def test_all_fields_set(self):
        """Test that all fields are set correctly."""
        annotation = fake_annotation()
        ch_annotation = ClickhouseAnnotation.from_domain(1, annotation)
        assert ch_annotation.model_fields_set == set(ClickhouseAnnotation.model_fields)

    def test_experiment_id_set(self):
        """Test that all fields are set correctly."""
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=uuid7(ms=lambda: 0, rand=lambda: 1)),
            context=Annotation.Context(experiment_id="test-experiment"),
        )
        ch_annotation = ClickhouseAnnotation.from_domain(1, annotation)
        assert ch_annotation.experiment_id == "test-experiment"
        assert ch_annotation.completion_id == uuid7(ms=lambda: 0, rand=lambda: 1)
