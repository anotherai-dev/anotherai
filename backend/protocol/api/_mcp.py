# ruff: noqa: B008
# pyright: reportCallInDefaultInitializer=false

from typing import Annotated, Any

from pydantic import Field

from core.domain.cache_usage import CacheUsage
from core.services.documentation_search import DocumentationSearch
from protocol.api import _mcp_utils
from protocol.api._api_models import (
    Agent,
    Annotation,
    CompleteAPIKey,
    CreateAPIKeyRequest,
    CreateViewResponse,
    Deployment,
    Experiment,
    Input,
    Message,
    Model,
    Page,
    PlaygroundOutput,
    QueryCompletionResponse,
    SearchDocumentationResponse,
    Tool,
    View,
)
from protocol.api._services import models_service

mcp = _mcp_utils.CustomFastMCP(
    "Another AI",
    middleware=[_mcp_utils.BaseMiddleware()],
    tool_serializer=_mcp_utils.tool_serializer,
)


@mcp.tool()
async def playground(
    models: str = Field(
        description="A comma separated list of models to use for the playground. Use list_models first to see available model IDs before selecting models",
    ),
    author_name: str = Field(
        description="The author of the experiment. E-g: 'Claude Code', 'user', 'my_script.py',etc.",
    ),
    agent_id: str = Field(
        description="The agent id to use for the playground. When a new experiment is requested, unless the user explicitly requests a new agent, reuse an existing agent if one exists that already performs the requested action. First call list_agents to see available agents and use an existing ID. Only create a new agent if none match or if the user explicitly requests it.",
    ),
    inputs: list[Input] | None = Field(
        default=None,
        description="""The inputs to use for the playground. A completion will be generated per input per version.
        An input can include a set of variables used in the templated prompt or a list of messages to be appended
        to the prompt. Either inputs or completion_query must
        be provided.""",
    ),
    completion_query: str | None = Field(
        None,
        description="🔄 PREFERRED for re-running experiments: SQL query to fetch completions and use the associated inputs. Must yield the input_variables and input_messages columns. Use this instead of query_completions() + inputs parameter when retrying existing completions.",
    ),
    prompts: list[list[Message]] | None = Field(
        default=None,
        description=f"""A list of prompt variations, where each prompt is a list of messages that will begin the message
        list sent to the model. The content of messages can be a Jinja2 template, in which case the input.variables
        will be used to render the message. The message json schema is {Message.model_json_schema()}""",
    ),
    temperatures: str = Field(
        default="1.0",
        description="A comma separated list of temperatures to use for the playground.",
    ),
    tool_lists: list[list[Tool]] | None = Field(
        default=None,
        description=f"""A list of tool lists to use for the playground. Each tool list will generate separate versions.
        Cannot be used with 'tools' parameter. The tool json schema is {Tool.model_json_schema()}""",
    ),
    output_schemas: list[dict[str, Any]] | None = Field(
        default=None,
        description="""A list of JSON schemas for structured output. Each schema will generate separate versions.
        Cannot be used with 'output_schema' parameter.""",
    ),
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata to attach to all completion requests",
    ),
    experiment_id: str | None = Field(
        None,
        description="Optional experiment ID to store the completions in. If not provided, a new experiment is created",
    ),
    experiment_description: str | None = Field(
        None,
        description="Description of the experiment. Required if experiment_id is not provided",
    ),
    experiment_title: str | None = Field(
        None,
        description="Title of the experiment. Required if experiment_id is not provided",
    ),
    use_cache: CacheUsage = Field(
        default="always",
        description="Whether to use the cache for the playground. If 'auto', the cache will be used if the temperature is 0 and no tools are enabled.",
    ),
) -> PlaygroundOutput:
    """
    Agent Reuse Policy:
    -------------------
    When creating a new experiment, always check for existing agents that perform similar tasks or have matching functionality.
    - Step 1: Use the list_agents tool to retrieve all available agents.
    - Step 2: If an agent exists whose purpose, configuration, or name matches the requested task, reuse that agent by specifying its agent_id in the experiment.
    - Step 3: Only create a new agent if:
        - No existing agent matches the requested action, or
        - The user explicitly requests a new, isolated agent for this experiment.
    - Step 4: If uncertain about agent compatibility, create a new agent to ensure proper functionality and avoid potential compatibility issues.

    Rationale:
    Reusing agents ensures experiment continuity, avoids unnecessary duplication, and makes it easier to compare results across runs.

    You have access to a playground to create a matrix of completions. A completion will be executed per:
    - input (variables and messages)
    - model
    - temperature
    - prompt variation
    - tool list (if tool_lists provided)
    - output schema (if output_schemas provided)
    All completions will be executed in parallel.
    For example if you supply:
    - 2 models
    - 2 temperatures
    - 2 prompt variations
    - 2 sets of input variables
    - 2 tool lists
    - 2 output schemas
    You will get 2x2x2x2x2x2=64 completions.

    Supports structured output via response_format parameter.
    Supports metadata attachment for tracking and observability.

    For providing inputs, you have two options:
    - inputs parameter: provide a list of inputs directly (for new experiments with custom data)
    - completion_query parameter: 🔄 PREFERRED for re-running experiments - provide a SQL query to fetch inputs from existing completions

    ✅ USE the completion_query parameter when:
    - "retry the last 50 completions"
    - "repeat the last 50 completions with positive user feedback"
    - Re-running any existing completions with different models/settings
    - Comparing performance across different model versions

    ❌ AVOID using the query_completions() tool to fetch data and then passing it to inputs parameter

    Examples:
    - Repeat the last 50 unique inputs completions:
    SELECT * FROM completions LIMIT 50 ORDER BY created_at DESC LIMIT 1 BY input_id LIMIT 50
    - Use all the runs from a specific experiment:
    SELECT * FROM completions WHERE id IN (SELECT arrayJoin(completion_ids) FROM experiments WHERE id = 'exp-billing-analysis')
    - Use all the runs that have been annotated today
    SELECT input_variables, input_messages FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.created_at >= now() - INTERVAL 1 DAY
    """

    return await (await _mcp_utils.playground_service()).run(
        agent_id=agent_id,
        inputs=inputs,
        completion_query=completion_query,
        models=models,
        prompts=prompts,
        temperatures=temperatures,
        tool_lists=tool_lists,
        output_schemas=output_schemas,
        metadata=metadata,
        author_name=author_name,
        experiment_id=experiment_id,
        experiment_description=experiment_description,
        experiment_title=experiment_title,
        use_cache=use_cache,
    )


# ------------------------------------------------------------
# Models


@mcp.tool()
async def list_models() -> list[Model]:
    return await models_service.list_models()


# ------------------------------------------------------------
# Agents


@mcp.tool()
async def list_agents() -> Page[Agent]:
    return await (await _mcp_utils.agent_service()).list_agents()


# ------------------------------------------------------------
# Experiments


@mcp.tool()
async def get_experiment(id: str) -> Experiment:
    return await (await _mcp_utils.experiment_service()).get_experiment(id)


@mcp.tool()
async def add_experiment_result(id: str, result: str):
    await (await _mcp_utils.experiment_service()).set_experiment_result(id, result)
    return "success"


# ------------------------------------------------------------
# Annotations


@mcp.tool()
async def get_annotations(
    experiment_id: str | None = None,
    completion_id: str | None = None,
    agent_id: str | None = None,
    since: str | None = None,
) -> Page[Annotation]:
    """
    Get all annotations for a completion or experiment.

    This tool retrieves all annotations that have been added within a specific context,
    allowing you to review feedback and comments on experiment outputs.

    For more advanced querying of annotations in relation to completions, use the query_completions tool with JOIN syntax.

    Args:
        experiment_id: Optional experiment ID to get annotations from.
        completion_id: Optional completion ID to get annotations from.
        agent_id: Optional agent ID to get annotations from.
        since: Optional ISO timestamp string to filter annotations added after this time

    Returns:
        Page of Annotation objects with well-defined structure. When specifying an experiment_id,
        all annotations for that experiment are included.

    Usage Examples:
        # Get all annotations made for a specific completion
        annotations = get_annotations(completion_id="completion_123")

        # Get only annotations added since a specific time for an experiment
        recent_annotations = get_annotations(experiment_id="sentiment_analysis_v1", since="2024-01-15T10:30:00")

    For more complex queries combining completions and annotations, use the query_completions tool.
    """
    return await (await _mcp_utils.annotation_service()).get_annotations(
        experiment_id=experiment_id,
        completion_id=completion_id,
        agent_id=agent_id,
        since=since,
    )


@mcp.tool()
async def add_annotations(
    annotations: list[Annotation] = Field(
        description="List of Annotation objects to add.",
    ),
) -> str:
    """
    Add multiple annotations to completions or experiments.

    This tool allows you to annotate specific fields or entire outputs from your experiment completions,
    individual model performance, or overall experiment design. Annotations help provide feedback
    on model performance, schema design, and output quality.


    Returns:
        None: Annotations are stored and can be retrieved using get_annotations()

    Key Path Examples:
        - None : Annotate the entire target (completion or experiment)
        - "suggested_actions[0]" : Annotate first item in array
        - "metadata.timestamp" : Annotate nested object property
        - "suggested_actions[0].action" : Annotate specific property of array item

    Usage Examples:
        # Add text comments to a completion
        add_annotations([
            {"id": "ann_1", "completion_id": "completion_123", "experiment_id": null, "key_path": null, "text": "Good overall analysis", "metric": null, "metadata": {"tags": "approval"}, "user_id": "analyst_123", "created_at": "2024-01-15T14:30:00", "updated_at": null},
            {"id": "ann_2", "completion_id": "completion_123", "experiment_id": null, "key_path": "sentiment", "text": "Correctly identified as positive", "metric": null, "metadata": {"tags": "approval"}, "user_id": "analyst_123", "created_at": "2024-01-15T14:30:01", "updated_at": null}
        ])

        # Add metrics to a completion
        add_annotations([
            {"id": "ann_3", "completion_id": "completion_123", "experiment_id": null, "key_path": null, "text": "High accuracy on test set", "metric": {"name": "accuracy", "value": 0.92}, "metadata": {}, "user_id": "analyst_123", "created_at": "2024-01-15T14:30:02", "updated_at": null},
            {"id": "ann_4", "completion_id": "completion_123", "experiment_id": null, "key_path": null, "text": "Professional tone detected", "metric": {"name": "tone", "value": 8.5}, "metadata": {}, "user_id": "analyst_123", "created_at": "2024-01-15T14:30:03", "updated_at": null}
        ])

        # Add user feedback and suggestions
        add_annotations([
            {"id": "ann_5", "completion_id": "completion_123", "experiment_id": null, "key_path": null, "text": "User found this helpful", "metric": {"name": "user_feedback", "value": 5.0}, "metadata": {"tags": "approval"}, "user_id": "user_456", "created_at": "2024-01-15T14:30:04", "updated_at": null},
            {"id": "ann_6", "completion_id": "completion_123", "experiment_id": null, "key_path": null, "text": "Consider adding examples:\n\n```suggestion\nAdd step-by-step examples\n```", "metric": null, "metadata": {"tags": "suggestion"}, "user_id": "user_101", "created_at": "2024-01-15T14:30:05", "updated_at": null}
        ])
    """
    await (await _mcp_utils.annotation_service()).add_annotations(annotations)
    return "success"


# ------------------------------------------------------------
# Documentation


def _get_description_search_documentation_tool() -> str:
    """Generate dynamic description for search_documentation tool."""
    available_pages = DocumentationSearch().get_available_pages_descriptions()

    return f"""🔍 **CRITICAL: Always search documentation before performing AnotherAI tasks.**

Search AnotherAI documentation OR fetch a specific documentation page.

     <mandatory_first_step>
     **BEFORE starting any AnotherAI task, you MUST:**
     1. First, read the "foundations" page to understand core concepts and architecture
     2. Search or read relevant documentation pages for the specific task you're performing
     3. Only proceed with other tools after consulting the appropriate documentation

     This ensures you have the correct context and approach for AnotherAI operations.
     </mandatory_first_step>

     <how_to_use>
     Enable MCP clients to explore AnotherAI documentation through a dual-mode search tool:
     1. Search mode ('query' parameter): Search across all documentation to find relevant documentation sections. Use search mode when you need to find information but don't know which specific page contains it.
     2. Direct navigation mode ('page' parameter): Fetch the complete content of a specific documentation page (see <available_pages> below for available pages). Use direct navigation mode when you want to read the full content of a specific page.

    We recommend combining search and direct navigation, and making multiple searches and direct navigations to get the most relevant knowledge.

    You must at least always read the "foundations" page before starting any work with AnotherAI, which contains the core concepts and architecture of AnotherAI.
    </how_to_use>

     <available_pages>
     The following documentation pages are available for direct access:

     {available_pages}
     </available_pages>

     <returns>
     - If using query: Returns a list of SearchResult objects with relevant documentation sections and source page references that you can use to navigate to the relevant page.
     - If using page: Returns the complete content of the specified documentation page as a string
     - Error message if both or neither parameters are provided, or if the requested page is not found
     </returns>"""


# TODO: generate the tool description dynamically
@mcp.tool(description=_get_description_search_documentation_tool())
async def search_documentation(
    query: str | None = Field(
        default=None,
        description="Search across all AnotherAI documentation. Use query when you need to find specific information across multiple pages or you don't know which specific page contains the information you need.",
    ),
    page: str | None = Field(
        default=None,
        description="Use page when you know which specific page contains the information you need.",
    ),
    programming_language: str | None = Field(
        default=None,
        description="The programming language to generate code examples for (e.g., 'python', 'typescript', 'javascript', 'go', 'rust', 'java', 'csharp'). This can help provide more relevant documentation with language-specific examples.",
    ),
) -> SearchDocumentationResponse:  # TODO: dedicated model ?
    return await _mcp_utils.documentation_service().search_documentation(
        query=query,
        page=page,
        programming_language=programming_language,
    )


# ------------------------------------------------------------
# Completions


# TODO: we should add comments to fields so that they show when describing the table
@mcp.tool()
async def query_completions(
    query: str = Field(
        description="SQL query to execute. Must use ClickHouse SQL syntax.",
    ),
) -> QueryCompletionResponse:
    """
    Exposes the clickhouse database to the user. The tool validates your SQL query and returns a URL to view the results in the web interface.
    Avoid using the query_completions tool to then pass the inputs to the playground tool. Instead, use the completion_query parameter of the playground tool.

    The completion table structured is defined below (in doubt, you can retrieve the structure using DESCRIBE TABLE completions).

    ```sql
    -- The unique identifier of the completion a UUID7
    id UUID,
    -- Auto generated from the id column, and used in sorting and partitioning
    -- When querying, it is always recommended to pass a created_at filter.
    created_at DateTime64(3) ALIAS UUIDv7ToDateTime(id),
    -- The agent id.
    agent_id String,
    -- Version ID
    version_id FixedString(32),
    version_model LowCardinality(String),
    -- Full version object, serialized as a json string
    version String,
    -- Input
    input_id FixedString(32),
    input_preview String,
    -- Messages part of the input, serialized as a json string
    input_messages String,
    -- Variables part of the input, serialized as a json string
    input_variables String,
    -- Output
    output_id FixedString(32),
    output_preview String,
    -- output messages, serialized as a json string
    output_messages String,
    -- output error, serialized as a json string. If empty the run was successful
    output_error String,
    -- full rendered list of messages sent for the final completion, not including the output messages.
    -- serialized as a json string. Due to its length, the column is highly compressed and filtering using
    -- the messages column is not recommended.
    messages String CODEC(ZSTD(3)),
    -- Duration in seconds, 0 is used as a default value
    -- and should be ignored in aggregations
    duration_seconds Float64,
    -- Cost in USD, 0 is used as a default value
    -- and should be ignored in aggregations
    cost_usd Float64,
    -- Metadata. Non strings are stored as stringified JSON. Strings are stored as is.
    metadata Map(String, String),
    -- The origin of the run
    source Enum('web' = 1, 'api' = 2, 'mcp' = 3),
    -- Traces
    traces Nested (
        kind String,
        model String,
        provider String,
        usage String,
        name String,
        tool_input_preview String,
        tool_output_preview String,
        duration_ds UInt16,
        cost_millionth_usd UInt32
    )
    ```

    Then the annotations table:
    ```sql
    created_at DateTime,
    id String,
    updated_at DateTime,
    agent_id LowCardinality(String),
    completion_id UUID,
    metric_name Nullable(String),
    metric_value_float Nullable(Float64),
    metric_value_str Nullable(String),
    metric_value_bool Nullable(Boolean),
    metadata Map(String, String),
    author_name String,
    text Nullable(String),
    ```

    And the experiments table:
    ```sql
    created_at DateTime,
    updated_at DateTime,
    id String,
    completion_ids Array(UUID),
    agent_id LowCardinality(String),
    metadata Map(String, String),
    title String,
    description String,
    result Nullable(String),
    ```

    Examples:
    - Filtering by created_at and agent_id
    SELECT * FROM completions WHERE created_at >= '2025-07-27' AND agent_id = 'customer-support-agent'
    - Filtering by run id
    SELECT * FROM completions WHERE id = '123e4567-e89b-12d3-a456-426614174000' and created_at = UUIDv7ToDateTime(toUUID('123e4567-e89b-12d3-a456-426614174000'))
    - Aggregating the cost and duration by agent_id
    SELECT agent_id, SUM(cost_usd) as total_cost, AVG(duration_seconds) as avg_duration FROM completions GROUP BY agent_id
    - Filtering on a specific metadata field
    SELECT * FROM completions WHERE metadata['user_id'] = 'a-user'
    - Filtering on a specific input field
    SELECT * FROM completions WHERE simpleJSONExtractString(input_variables, 'name') = 'John'
    - Filtering on a specific annotation
    SELECT * FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.metric_name = 'user_feedback' AND annotations.metric_value_str = 'positive' AND annotations.created_at >= subtractDays(now(), 7)
    - Get completions with annotations from specific users
    SELECT completions.id, completions.cost_usd, annotations.text, annotations.author_name FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.author_name = 'analyst_123'
    - Find completions with recent positive feedback
    SELECT completions.id, completions.agent_id, annotations.text, annotations.created_at FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.metric_name = 'user_feedback' AND annotations.metric_value_str = 'positive' AND annotations.created_at >= subtractDays(now(), 7)
    """
    return await (await _mcp_utils.completion_service()).query_completions(query)


# ------------------------------------------------------------
# Dashboards


# TODO: add pagination and limit
@mcp.tool()
async def list_views() -> Page[View]:
    """List all views"""
    return await (await _mcp_utils.view_service()).list_views()


@mcp.tool()
async def get_view(id: str) -> View:
    """Get a view by id"""
    return await (await _mcp_utils.view_service()).get_view(id)


@mcp.tool(
    description=f"""Create a new view or update an existing view. If no dashboard id is provided, the "default" dashboard is used.  # nosec B608
If a dashboard with the provided id does not exist, it will be created.

**Best Practice**: Avoid using `SELECT *` in your queries as it returns all 40+ columns. Instead:
1. First use `query_completions('DESCRIBE TABLE completions')` to see all available fields
2. Select only the fields relevant to your use case
3. This creates cleaner, more performant views

**Important for Table Views**: When creating table views, include the 'id' column in your SELECT statement if you want rows to be clickable for viewing completion details. Without the 'id' column, rows will display data but won't be interactive.

**Sort Order Best Practices:**
- Time series graphs (line/bar): Use `ORDER BY date ASC` to display chronologically from past to present
- Tables showing recent completions: Use `ORDER BY created_at DESC` to show newest first
- Tables showing daily aggregates: Consider the use case - ASC for historical analysis, DESC for monitoring recent trends

Example workflow:
```python
# Step 1: Explore available fields
query_completions(query="DESCRIBE TABLE completions")

# Step 2: Create view with specific fields (including 'id' for clickable rows)
create_or_update_view(
    view={{
        "id": "experiment-v1-analysis",
        "title": "Experiment V1 Analysis",
        "query": "SELECT id, created_at, agent_id, cost_usd, duration_seconds FROM completions WHERE metadata['experiment'] = 'v1'",
        "graph": {{"type": "table"}}
    }}
)
```

The view object should respect the following schema:
{View.model_json_schema()}

Returns the view url that can be used to access the view in the Another AI app.
    """,  # noqa: S608 # not a sql query
)
async def create_or_update_view(
    view: Annotated[View, Field(description="The view to create or update")],
) -> CreateViewResponse:
    return await (await _mcp_utils.view_service()).create_or_update_mcp(view)


# ------------------------------------------------------------
# API Keys


@mcp.tool()
async def create_api_key(name: str) -> CompleteAPIKey:
    """Create a new API key that can be used to authenticate with the Another AI MCP and API"""
    return await (await _mcp_utils.organization_service()).create_api_key(CreateAPIKeyRequest(name=name))


# ------------------------------------------------------------
# Deployments


@mcp.tool()
async def list_deployments(
    agent_id: str | None = Field(
        default=None,
        description="The agent id to filter deployments by",
    ),
    limit: int = Field(
        default=10,
        description="The number of deployments to return",
    ),
    page_token: str | None = Field(
        default=None,
        description="The page token to use for pagination",
    ),
) -> Page[Deployment]:
    """List all deployments"""
    return await (await _mcp_utils.deployment_service()).list_deployments(
        agent_id=agent_id,
        limit=limit,
        page_token=page_token,
        include_archived=False,
    )


@mcp.tool()
async def create_or_update_deployment(
    agent_id: str = Field(
        description="The agent id to deploy the version to",
    ),
    version_id: str = Field(
        description="The version id to deploy. Can be found in an experiment or a completion.",
    ),
    deployment_id: str = Field(
        # TODO: update description and examples based on tests. Make sure field in _api_models.py is updated too.
        description="The id of the deployment",
        examples=["my-agent-id:production#1"],
    ),
    author_name: str = Field(
        description="The name of the author of the deployment",
    ),
) -> Deployment | str:
    """Create a new deployment or update an existing deployment if id matches.

    Note that overriding a deployment with a new id is only possible if the variable
    (aka version.input_variables_schema) and response formats (version.output_schema) are compatible
    between the deployments. Schemas are considered compatible if all their fields have the same name, type
    and properties.

    Updating an existing deployment needs user confirmation. You will be provided the URL where a user can
    confirm the update.
    """
    return await (await _mcp_utils.deployment_service()).upsert_deployment(
        agent_id=agent_id,
        version_id=version_id,
        deployment_id=deployment_id,
        author_name=author_name,
    )
