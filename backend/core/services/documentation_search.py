import json
import os
from pathlib import Path
from typing import Any

import structlog

from core.agents.search_documentation import search_documentation_agent
from core.domain.documentation_section import DocumentationSection

_LOCAL_FILE_EXTENSIONS: list[str] = [".mdx", ".md"]

log = structlog.get_logger(__name__)


def _doc_directory():
    current = Path(__file__).parent
    for _ in range(5):
        doc_dir = current / "docs"
        if doc_dir.exists() and doc_dir.is_dir():
            return str(doc_dir)
        current = current.parent
    raise ValueError("Docs directory not found")


_LOCAL_DOCS_DIR: str = _doc_directory()


# TODO: test
# TODO: find a better name
class DocumentationSearch:

    def __init__(self):
        self._config = self._load_config()
        self._current_env = self._get_environment()

    def get_available_pages_descriptions(self) -> str:
        """Generate formatted descriptions of all available documentation pages for MCP tool docstring."""
        # TODO: cache ?
        all_sections = self.get_all_doc_sections()

        if not all_sections:
            return "No documentation pages found."

        # Build simple list of pages with descriptions
        result_lines: list[str] = []

        for section in sorted(all_sections, key=lambda s: s.file_path):
            page_path = section.file_path
            summary = self._extract_summary_from_content(section.content)
            result_lines.append(f"     - '{page_path}' - {summary}")

        return "\n".join(result_lines)

    def _extract_summary_from_content(self, content: str) -> str:
        """Extract a summary from markdown content."""
        lines = content.split("\n")

        # Look for frontmatter summary
        if lines and lines[0].strip() == "---":
            for i in range(1, min(20, len(lines))):  # Check first 20 lines for frontmatter
                line = lines[i].strip()
                if line == "---":
                    break
                if line.startswith("summary:"):
                    return line.split("summary:", 1)[1].strip().strip("\"'")

        # Fallback when no summary is found
        return ""

    def get_all_doc_sections(self) -> list[DocumentationSection]:
        doc_sections: list[DocumentationSection] = []
        base_dir: str = _LOCAL_DOCS_DIR
        if not os.path.isdir(base_dir):
            log.error("Documentation directory not found", extra={"base_dir": base_dir})
            return []

        for root, _, files in os.walk(base_dir):
            for file in files:
                if not file.endswith(tuple(_LOCAL_FILE_EXTENSIONS)):
                    continue
                if file.startswith(".") or ".private" in file:  # Ignore hidden files and private pages
                    continue
                full_path: str = os.path.join(root, file)
                relative_path: str = os.path.relpath(full_path, base_dir)
                try:
                    with open(full_path) as f:
                        content = f.read()
                        # Apply variable substitution
                        content = self._substitute_variables(content)
                        doc_sections.append(
                            DocumentationSection(
                                file_path=relative_path.replace(".mdx", "").replace(".md", ""),
                                content=content,
                            ),
                        )
                except Exception as e:
                    log.exception(
                        "Error reading or processing documentation file",
                        full_path=full_path,
                        exc_info=e,
                    )
        # Sort by title to ensure consistent ordering, for example to trigger LLM provider caching
        return sorted(doc_sections, key=lambda x: x.file_path)

    async def _get_documentation_by_path(self, pathes: list[str]) -> list[DocumentationSection]:
        all_doc_sections: list[DocumentationSection] = self.get_all_doc_sections()
        found_sections = [doc_section for doc_section in all_doc_sections if doc_section.file_path in pathes]

        # Check if any paths were not found
        found_paths = {doc_section.file_path for doc_section in found_sections}
        missing_paths = set(pathes) - found_paths

        if missing_paths:
            log.error("Documentation not found", paths=missing_paths)

        return found_sections

    async def search_documentation_by_query(
        self,
        query: str,
        usage_context: str | None = None,
    ) -> list[DocumentationSection]:
        all_doc_sections: list[DocumentationSection] = self.get_all_doc_sections()

        # TODO: have a static list of the most relevant docs as a fallback ?
        fallback_docs_sections: list[DocumentationSection] = []

        try:
            result = await search_documentation_agent(
                query=query,
                available_doc_sections=all_doc_sections,
                usage_context=usage_context,
            )
        except Exception as e:
            log.exception("Error in search documentation agent", exc_info=e)
            return fallback_docs_sections

        if not result:
            log.error("search_documentation_agent did not return any parsed result", query=query)
            return fallback_docs_sections

        relevant_doc_sections: list[str] = (
            result.relevant_documentation_file_paths if result and result.relevant_documentation_file_paths else []
        )

        # Log warning for cases where the agent has reported a missing doc sections
        if result.missing_doc_sections_feedback:
            log.warning(
                "Documentation search agent has reported a missing doc sections",
                missing_doc_sections_feedback=result.missing_doc_sections_feedback,
            )

        # Log warning for cases where the agent has reported an unsupported feature
        if result.unsupported_feature_feedback:
            log.warning(
                "Documentation search agent has reported an unsupported feature",
                unsupported_feature_feedback=result.unsupported_feature_feedback,
            )

        # If agent did not report any missing doc sections but no relevant doc sections were found, we log a warning too
        if not result.missing_doc_sections_feedback and not result.relevant_documentation_file_paths:
            log.warning(
                "Documentation search agent has not found any relevant doc sections",
                query=query,
            )

        return [
            document_section
            for document_section in all_doc_sections
            if document_section.file_path in relevant_doc_sections
        ]

    async def get_documentation_by_path(self, pathes: list[str]) -> list[DocumentationSection]:
        all_doc_sections: list[DocumentationSection] = self.get_all_doc_sections()
        found_sections = [doc_section for doc_section in all_doc_sections if doc_section.file_path in pathes]

        # Check if any paths were not found
        found_paths = {doc_section.file_path for doc_section in found_sections}
        missing_paths = set(pathes) - found_paths

        if missing_paths:
            log.error("Documentation not found", paths=missing_paths)

        return found_sections

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from config.json file."""
        config_path = Path(_LOCAL_DOCS_DIR) / "config.json"

        if not config_path.exists():
            log.warning("Documentation config file not found", path=str(config_path))
            return {}

        try:
            with open(config_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.error("Error loading documentation config", path=str(config_path), error=str(e))
            return {}

    def _get_environment(self) -> str:
        """Get current environment from env var or default to local."""
        return os.getenv("ANOTHERAI_DOCS_ENV", "local")

    def _substitute_variables(self, content: str) -> str:
        """Substitute variables in documentation content."""
        # Check for environment variable override first
        api_url = os.getenv("ANOTHERAI_DOCS_API_URL")

        if not api_url:
            # Try to get from environment-specific config
            env_config = self._config.get("environments", {}).get(self._current_env, {})
            api_url = env_config.get("API_URL")

            if not api_url:
                # Fall back to default
                api_url = self._config.get("default", {}).get("API_URL", "https://api.anotherai.dev")

        # Check for WEB_APP_URL
        web_app_url = os.getenv("ANOTHERAI_DOCS_WEB_APP_URL")

        if not web_app_url:
            # Try to get from environment-specific config
            env_config = self._config.get("environments", {}).get(self._current_env, {})
            web_app_url = env_config.get("WEB_APP_URL")

            if not web_app_url:
                # Fall back to default
                web_app_url = self._config.get("default", {}).get("WEB_APP_URL", "http://localhost:3000")

        # Replace variables
        content = content.replace("{{API_URL}}", api_url)
        content = content.replace("{{WEB_APP_URL}}", web_app_url)

        return content
