import pytest

from core.domain.models.model_data_supports import ModelDataIOSupports


class TestModelDataIOSupports:
    @pytest.mark.parametrize(
        ("supports", "compared_to", "expected"),
        [
            pytest.param(
                ModelDataIOSupports(supports_input_image=True, supports_input_pdf=True, supports_input_audio=True),
                ModelDataIOSupports(supports_input_image=True, supports_input_pdf=False, supports_input_audio=False),
                set[str](),
                id="all_supports",
            ),
            pytest.param(
                ModelDataIOSupports(supports_input_image=False, supports_input_pdf=True, supports_input_audio=True),
                ModelDataIOSupports(supports_input_image=True, supports_input_pdf=False, supports_input_audio=False),
                {"supports_input_image"},
                id="missing_input_image",
            ),
            pytest.param(
                ModelDataIOSupports(supports_input_image=False, supports_input_pdf=False, supports_input_audio=False),
                ModelDataIOSupports(supports_input_image=True, supports_input_pdf=True, supports_input_audio=True),
                {"supports_input_image", "supports_input_pdf", "supports_input_audio"},
                id="missing_multiple_supports",
            ),
        ],
    )
    def test_missing_io_supports(
        self,
        supports: ModelDataIOSupports,
        compared_to: ModelDataIOSupports,
        expected: set[str],
    ):
        assert supports.missing_io_supports(compared_to) == expected
