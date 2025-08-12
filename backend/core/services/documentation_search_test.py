import json
import os
from unittest.mock import mock_open, patch

import pytest

from core.services.documentation_search import DocumentationSearch


class TestDocumentationSearch:
    """Test cases for DocumentationSearch variable substitution functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration data."""
        return {
            "environments": {
                "local": {
                    "API_URL": "http://localhost:8000",
                },
                "production": {
                    "API_URL": "https://api.anotherai.dev",
                },
            },
            "default": {
                "API_URL": "https://api.anotherai.dev",
            },
        }

    @pytest.fixture
    def documentation_search(self):
        """Create a DocumentationSearch instance for testing."""
        return DocumentationSearch()

    def test_substitute_variables_with_default(self, documentation_search, mock_config):
        """Test variable substitution with default values."""
        # Mock the config loading
        documentation_search._config = mock_config
        documentation_search._current_env = "production"

        content = "API endpoint: {{API_URL}}/v1/models"
        result = documentation_search._substitute_variables(content)

        assert result == "API endpoint: https://api.anotherai.dev/v1/models"

    def test_substitute_variables_with_local_environment(self, documentation_search, mock_config):
        """Test variable substitution with local environment."""
        documentation_search._config = mock_config
        documentation_search._current_env = "local"

        content = "Connect to {{API_URL}}/v1/chat/completions"
        result = documentation_search._substitute_variables(content)

        assert result == "Connect to http://localhost:8000/v1/chat/completions"

    @patch.dict(os.environ, {"ANOTHERAI_DOCS_API_URL": "http://custom.example.com"})
    def test_substitute_variables_with_env_override(self, documentation_search, mock_config):
        """Test that environment variables override config values."""
        documentation_search._config = mock_config
        documentation_search._current_env = "production"

        content = "API: {{API_URL}}"
        result = documentation_search._substitute_variables(content)

        # Environment variable should take precedence
        assert result == "API: http://custom.example.com"

    def test_substitute_variables_no_placeholder(self, documentation_search, mock_config):
        """Test content without placeholders remains unchanged."""
        documentation_search._config = mock_config
        documentation_search._current_env = "production"

        content = "This is regular content without any variables."
        result = documentation_search._substitute_variables(content)

        assert result == content

    def test_substitute_variables_multiple_occurrences(self, documentation_search, mock_config):
        """Test substitution with multiple occurrences of the same variable."""
        documentation_search._config = mock_config
        documentation_search._current_env = "production"

        content = """
        Main API: {{API_URL}}
        Backup API: {{API_URL}}
        Documentation: {{API_URL}}/docs
        """
        result = documentation_search._substitute_variables(content)

        expected = """
        Main API: https://api.anotherai.dev
        Backup API: https://api.anotherai.dev
        Documentation: https://api.anotherai.dev/docs
        """
        assert result == expected

    def test_substitute_web_app_url_variable(self, documentation_search):
        """Test WEB_APP_URL variable substitution."""
        # Test with production environment
        documentation_search._config = {
            "environments": {
                "production": {
                    "API_URL": "https://api.anotherai.dev",
                    "WEB_APP_URL": "https://anotherai.dev",
                },
                "local": {
                    "API_URL": "http://localhost:8000",
                    "WEB_APP_URL": "http://localhost:3000",
                },
            },
            "default": {
                "API_URL": "http://localhost:8000",
                "WEB_APP_URL": "http://localhost:3000",
            },
        }
        documentation_search._current_env = "production"

        content = "Visit the playground at {{WEB_APP_URL}}/agents/my-agent/playground"
        result = documentation_search._substitute_variables(content)

        assert result == "Visit the playground at https://anotherai.dev/agents/my-agent/playground"

        # Test with local environment
        documentation_search._current_env = "local"
        result = documentation_search._substitute_variables(content)

        assert result == "Visit the playground at http://localhost:3000/agents/my-agent/playground"

    def test_substitute_variables_unknown_variable(self, documentation_search, mock_config):
        """Test that unknown variables are left unchanged."""
        documentation_search._config = mock_config
        documentation_search._current_env = "production"

        content = "Known: {{API_URL}}, Unknown: {{UNKNOWN_VAR}}"
        result = documentation_search._substitute_variables(content)

        assert result == "Known: https://api.anotherai.dev, Unknown: {{UNKNOWN_VAR}}"

    @patch.dict(os.environ, {"ANOTHERAI_DOCS_ENV": "local"})
    def test_get_environment_from_env_var(self, documentation_search):
        """Test environment detection from environment variable."""
        env = documentation_search._get_environment()
        assert env == "local"

    def test_get_environment_default(self, documentation_search):
        """Test default environment when no env var is set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove ANOTHERAI_DOCS_ENV if it exists
            os.environ.pop("ANOTHERAI_DOCS_ENV", None)
            env = documentation_search._get_environment()
            assert env == "local"

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_load_config_success(self, mock_exists, mock_file, documentation_search, mock_config):
        """Test successful config loading from file."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(mock_config)

        config = documentation_search._load_config()
        assert config == mock_config
        mock_file.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_load_config_file_not_found(self, mock_exists, documentation_search):
        """Test config loading when file doesn't exist."""
        mock_exists.return_value = False

        config = documentation_search._load_config()

        # Should return empty dict when config file not found
        assert config == {}

    def test_substitute_variables_with_missing_environment(self, documentation_search, mock_config):
        """Test fallback to default when environment is not in config."""
        documentation_search._config = mock_config
        documentation_search._current_env = "staging"  # Not in config

        content = "API: {{API_URL}}"
        result = documentation_search._substitute_variables(content)

        # Should fall back to default
        assert result == "API: https://api.anotherai.dev"
