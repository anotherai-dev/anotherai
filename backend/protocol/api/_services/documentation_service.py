from typing import final

from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.services.documentation.documentation_search import DocumentationSearch
from protocol.api._api_models import SearchDocumentationResponse


@final
class DocumentationService:
    def __init__(
        self,
        documentation_search: DocumentationSearch,
    ):
        self._documentation_search = documentation_search

    async def search_documentation(
        self,
        query: str | None = None,
        page: str | None = None,
        programming_language: str | None = None,
    ) -> SearchDocumentationResponse:
        """Search WorkflowAI documentation OR fetch a specific documentation page.

        Args:
            query: Search across all documentation to find relevant content snippets
            page: Direct access to specific documentation page

        Returns:
            LegacyMCPToolReturn with either search results or page content
        """
        if query and page:
            raise BadRequestError("Use either 'query' OR 'page' parameter, not both")

        if query:
            return await self._search_documentation_by_query(query)

        if page:
            return await self._get_documentation_page(page)

        raise BadRequestError("Provide either 'query' or 'page' parameter")

    async def _search_documentation_by_query(self, query: str) -> SearchDocumentationResponse:
        """Search documentation using query and return snippets."""

        usage_context = """The query was made by an MCP (Model Context Protocol) client such as Cursor IDE and other
code editors.

Your primary purpose is to help developers find the most relevant WorkflowAI documentation sections to answer their
specific queries about building, deploying, and using AI agents.
"""
        relevant_sections = await self._documentation_search.search_documentation_by_query(
            query,
            usage_context,
        )

        # Convert to SearchResult format with content snippets
        query_results = [
            SearchDocumentationResponse.QueryResult(
                content_snippet=section.content,
                source_page=section.file_path,
            )
            for section in relevant_sections
        ]

        # Always add foundations page
        # TODO: try to return the foundations page only once, per chat, but might be difficult since `mcp-session-id`
        # is probably not scoped to a chat (for example, on CursorAI, multiple chat tabs can be open at the same time,
        # using (probably) the same `mcp-session-id`)
        if "foundations" not in [section.file_path for section in relevant_sections]:
            # @guillaume suggested to add a `read_foundations: true, false`
            # parameter to the search_documentation MCP tool
            sections = await self._documentation_search.get_documentation_by_path(["foundations"])
            query_results.append(
                SearchDocumentationResponse.QueryResult(
                    content_snippet=sections[0].content if sections else "",
                    source_page="foundations.mdx",
                ),
            )

        if len(query_results) == 0:
            raise ObjectNotFoundError("No relevant documentation sections found for query")

        return SearchDocumentationResponse(query_results=query_results)

    async def _get_documentation_page(self, page: str) -> SearchDocumentationResponse:
        """Get specific documentation page content."""

        sections = await self._documentation_search.get_documentation_by_path([page])

        # Find the requested page
        if sections:
            return SearchDocumentationResponse(page_content=sections[0].content)

        # Page not found - list available pages for user reference
        all_sections = self._documentation_search.get_all_doc_sections()
        available_pages = [section.file_path for section in all_sections]

        raise ObjectNotFoundError(f"Page '{page}' not found. Available pages: {', '.join(available_pages)}")
