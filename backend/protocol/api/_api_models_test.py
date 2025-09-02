from core.domain.version import Version


class TestVersion:
    def test_minimal_payload(self):
        only_model = Version.model_validate(
            {
                "model": "gpt-4o",
            },
        )
        assert only_model.model == "gpt-4o"
