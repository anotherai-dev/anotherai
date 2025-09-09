import os

import structlog

from core.agents.search_documentation import search_documentation_agent
from core.domain.documentation_section import DocumentationSection
from core.services.documentation.documentation_config import (
    DocumentationConfig,
    default_docs_config,
)

_LOCAL_FILE_EXTENSIONS: list[str] = [".mdx", ".md"]

log = structlog.get_logger(__name__)


_DEFAULT_DOCS_CONFIG = default_docs_config()


# TODO: test
# TODO: find a better name
class DocumentationSearch:
    def __init__(self, config: DocumentationConfig = _DEFAULT_DOCS_CONFIG):
        self._config = config

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
        # TODO: we could load all the sections once and cache them
        doc_sections: list[DocumentationSection] = []

        for root, _, files in os.walk(self._config.directory):
            for file in files:
                if not file.endswith(tuple(_LOCAL_FILE_EXTENSIONS)):
                    continue
                if file.startswith(".") or ".private" in file:  # Ignore hidden files and private pages
                    continue
                full_path: str = os.path.join(root, file)
                relative_path: str = os.path.relpath(full_path, self._config.directory)
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

    def _offline_documentation_search(  # noqa: C901
        self,
        query: str,
        all_doc_sections: list[DocumentationSection],
    ) -> list[DocumentationSection]:
        """Simple offline search using basic text matching and scoring."""
        if not query.strip():
            return []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_sections = []

        if "workflowai" in query_lower:

            def workflowai_adjustment(file_path: str) -> int:
                if "workflowai" in file_path:
                    return 100
                return 0
        else:

            def workflowai_adjustment(file_path: str) -> int:
                return 0

        for section in all_doc_sections:
            score = 0
            content_lower = section.content.lower()
            path_lower = section.file_path.lower()

            # Exact phrase match in content (high score)
            if query_lower in content_lower:
                score += 10

            # Exact phrase match in file path (high score)
            if query_lower in path_lower:
                score += 15

            # Word matches in content
            content_words = set(content_lower.split())
            matching_words = query_words.intersection(content_words)
            score += len(matching_words) * 2

            # Word matches in file path (weighted higher)
            path_words = set(path_lower.split("/"))
            path_matches = query_words.intersection(path_words)
            score += len(path_matches) * 5

            score += workflowai_adjustment(path_lower)

            if score > 0:
                scored_sections.append((section, score))

        # Sort by score (highest first) and return top 5
        def get_score(item: tuple[DocumentationSection, int]) -> int:
            return item[1]

        scored_sections.sort(key=get_score, reverse=True)
        return [section for section, _ in scored_sections[:5]]

    async def search_documentation_by_query(
        self,
        query: str,
        usage_context: str | None = None,
    ) -> list[DocumentationSection]:
        all_doc_sections: list[DocumentationSection] = self.get_all_doc_sections()

        # Removed fallback_docs_sections as we now use offline search as fallback

        try:
            result = await search_documentation_agent(
                query=query,
                available_doc_sections=all_doc_sections,
                usage_context=usage_context,
            )
        except Exception as e:
            log.exception("Error in search documentation agent, falling back to offline search", exc_info=e)
            return self._offline_documentation_search(query, all_doc_sections)

        if not result:
            log.error(
                "search_documentation_agent did not return any parsed result, falling back to offline search",
                query=query,
            )
            return self._offline_documentation_search(query, all_doc_sections)

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

        # If agent did not report any missing doc sections but no relevant doc sections were found, use offline search
        if not result.missing_doc_sections_feedback and not result.relevant_documentation_file_paths:
            log.warning(
                "Documentation search agent has not found any relevant doc sections, falling back to offline search",
                query=query,
            )
            return self._offline_documentation_search(query, all_doc_sections)

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

    def _substitute_variables(self, content: str) -> str:
        """Substitute variables in documentation content."""
        for key, value in self._config.variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    async def search_documentation_offline(self, query: str) -> list[DocumentationSection]:
        """Direct offline search without using the LLM agent."""
        all_doc_sections: list[DocumentationSection] = self.get_all_doc_sections()
        return self._offline_documentation_search(query, all_doc_sections)
