# pyright: reportPrivateUsage=false

import json
import os
from typing import Any
from unittest.mock import mock_open, patch

import pytest

from core.domain.documentation_section import DocumentationSection
from core.services.documentation_search import DocumentationSearch


@pytest.fixture
def mock_config():
    """Mock configuration data."""
    return {
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


@pytest.fixture
def documentation_search(mock_config: dict[str, Any]):
    """Create a DocumentationSearch instance for testing."""
    return DocumentationSearch(config=mock_config, current_env="production")


class TestSubstituteVariables:
    def test_substitute_variables_with_default(
        self,
        documentation_search: DocumentationSearch,
    ):
        """Test variable substitution with default values."""

        content = "API endpoint: {{API_URL}}/v1/models"
        result = documentation_search._substitute_variables(content)

        assert result == "API endpoint: https://api.anotherai.dev/v1/models"

    def test_substitute_variables_with_local_environment(self, documentation_search: DocumentationSearch):
        """Test variable substitution with local environment."""
        documentation_search._current_env = "local"

        content = "Connect to {{API_URL}}/v1/chat/completions"
        result = documentation_search._substitute_variables(content)

        assert result == "Connect to http://localhost:8000/v1/chat/completions"

    @patch.dict(os.environ, {"ANOTHERAI_DOCS_API_URL": "http://custom.example.com"})
    def test_substitute_variables_with_env_override(self, documentation_search: DocumentationSearch):
        """Test that environment variables override config values."""

        content = "API: {{API_URL}}"
        result = documentation_search._substitute_variables(content)

        # Environment variable should take precedence
        assert result == "API: http://custom.example.com"

    def test_substitute_variables_no_placeholder(self, documentation_search: DocumentationSearch):
        """Test content without placeholders remains unchanged."""

        content = "This is regular content without any variables."
        result = documentation_search._substitute_variables(content)

        assert result == content

    def test_substitute_variables_multiple_occurrences(self, documentation_search: DocumentationSearch):
        """Test substitution with multiple occurrences of the same variable."""

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

    def test_substitute_web_app_url_variable(self, documentation_search: DocumentationSearch):
        """Test WEB_APP_URL variable substitution."""

        content = "Visit the playground at {{WEB_APP_URL}}/agents/my-agent/playground"
        result = documentation_search._substitute_variables(content)

        assert result == "Visit the playground at https://anotherai.dev/agents/my-agent/playground"

        # Test with local environment
        documentation_search._current_env = "local"
        result = documentation_search._substitute_variables(content)

        assert result == "Visit the playground at http://localhost:3000/agents/my-agent/playground"

    def test_substitute_variables_unknown_variable(self, documentation_search: DocumentationSearch):
        """Test that unknown variables are left unchanged."""

        content = "Known: {{API_URL}}, Unknown: {{UNKNOWN_VAR}}"
        result = documentation_search._substitute_variables(content)

        assert result == "Known: https://api.anotherai.dev, Unknown: {{UNKNOWN_VAR}}"

    def test_substitute_variables_with_missing_environment(self, documentation_search: DocumentationSearch):
        """Test fallback to default when environment is not in config."""

        content = "API: {{API_URL}}"
        result = documentation_search._substitute_variables(content)

        # Should fall back to default
        assert result == "API: https://api.anotherai.dev"


class TestOfflineDocumentationSearch:
    def test_offline_documentation_search_basic(self, documentation_search: DocumentationSearch):
        """Test basic offline search functionality."""

        # Create test documents
        sections = [
            DocumentationSection(
                file_path="authentication/api-keys",
                content="Learn how to authenticate using API keys. Generate and manage your API keys.",
            ),
            DocumentationSection(
                file_path="models/openai",
                content="Configure OpenAI models in your application. Set up GPT-4 and other models.",
            ),
            DocumentationSection(
                file_path="deployment/docker",
                content="Deploy your application using Docker containers. Configure environment variables.",
            ),
        ]

        # Test API key search
        results = documentation_search._offline_documentation_search("API keys", sections)
        assert len(results) > 0
        assert results[0].file_path == "authentication/api-keys"

        # Test model search
        results = documentation_search._offline_documentation_search("OpenAI models", sections)
        assert len(results) > 0
        assert results[0].file_path == "models/openai"

        # Test deployment search
        results = documentation_search._offline_documentation_search("docker deployment", sections)
        assert len(results) > 0
        assert results[0].file_path == "deployment/docker"

    def test_offline_documentation_search_empty_query(self, documentation_search: DocumentationSearch):
        """Test offline search with empty query."""
        sections = [
            DocumentationSection(file_path="test", content="test content"),
        ]

        results = documentation_search._offline_documentation_search("", sections)
        assert len(results) == 0

        results = documentation_search._offline_documentation_search("   ", sections)
        assert len(results) == 0

    def test_offline_documentation_search_no_matches(self, documentation_search: DocumentationSearch):
        """Test offline search with no matching documents."""
        sections = [
            DocumentationSection(file_path="test", content="completely different content"),
        ]

        results = documentation_search._offline_documentation_search("nonexistent query", sections)
        assert len(results) == 0

    def test_offline_documentation_search_scoring(self, documentation_search: DocumentationSearch):
        """Test that search results are properly scored and ranked."""

        sections = [
            DocumentationSection(
                file_path="other/document",
                content="This mentions authentication briefly.",
            ),
            DocumentationSection(
                file_path="authentication/guide",
                content="Complete authentication guide with examples and best practices.",
            ),
        ]

        results = documentation_search._offline_documentation_search("authentication", sections)
        assert len(results) == 2
        # The authentication/guide should rank higher due to path matching
        assert results[0].file_path == "authentication/guide"

    def test_offline_documentation_search_workflowai_migration(self, documentation_search: DocumentationSearch):
        sections = documentation_search.get_all_doc_sections()
        results = documentation_search._offline_documentation_search("Migrate from WorkflowAI to AnotherAI", sections)
        assert len(results) > 0
        assert results[0].file_path.endswith("migrate-from-workflowai")


class TestLoadConfig:
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
