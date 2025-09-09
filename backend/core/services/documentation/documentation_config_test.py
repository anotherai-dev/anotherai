# pyright: reportPrivateUsage=false


from core.services.documentation.documentation_config import _default_docs_directory


def test_default_docs_directory():
    path, config = _default_docs_directory()
    assert path.endswith("docs")
    assert config.environments
    assert config.default
