"""Models exchanged by the API and MCP.
Do not include validation or conversion logic here. Logic should be included either in a service
or in the conversion layer."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from core.utils.fields import datetime_factory


class Page[T](BaseModel):
    """A page of results with cursor-based pagination."""

    items: list[T]
    total: int
    next_page_token: str | None = Field(
        default=None,
        description="Token to fetch the next page of results. None if this is the last page.",
    )
    previous_page_token: str | None = Field(
        default=None,
        description="Token to fetch the previous page of results. None if this is the first page.",
    )


class CreateAgentRequest(BaseModel):
    id: str
    name: str | None = None


class Agent(BaseModel):
    id: str = Field(description="A user defined identifier of the agent.")
    uid: int = Field(description="The unique integer identifier of the agent. Can be used to filter completions")
    name: str
    created_at: datetime


class ModelWithID(BaseModel):
    id: str


class Tool(BaseModel):
    name: str = Field(description="The name of the tool")
    description: str | None = Field(
        default=None,
        description="The description of the tool",
    )
    input_schema: dict[str, Any] = Field(description="The input class of the tool")


class ToolCallRequest(BaseModel):
    id: str = Field(description="The id of the tool call request")
    name: str = Field(description="The name of the tool")
    arguments: dict[str, Any] = Field(description="The arguments of the tool")


class ToolCallResult(BaseModel):
    id: str = Field(description="The id of the tool call result")
    output: Any | None = Field(description="The output of the tool")
    error: str | None = Field(description="The error of the tool")


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "developer", "tool"]

    class Content(BaseModel):
        """A content of a message. Only a single field can be present at a time."""

        text: str | None = None
        object: dict[str, Any] | list[Any] | None = None
        image_url: str | None = None
        audio_url: str | None = None
        tool_call_request: ToolCallRequest | None = None  # function_call in response API
        tool_call_result: ToolCallResult | None = None  # function_call_output in response API
        reasoning: str | None = None

    # Never a list[Any] to avoid conflicts with the list[Content]
    content: list[Content] | str | dict[str, Any]


class OutputSchema(BaseModel):
    id: str = Field(description="The id of the output schema. Auto generated from the json schema")
    json_schema: dict[str, Any] = Field(description="The JSON schema of the output")


class Version(BaseModel):
    id: str = Field(description="The id of the version. Auto generated.", default="")
    model: str
    # Default values match OpenAI API defaults (temperature=1.0, top_p=1.0)
    temperature: float = 1.0
    top_p: float = 1.0
    tools: list[Tool] | None = Field(
        default=None,
        description="A list of tools that the model can use. If empty, no tools are used.",
    )

    prompt: list[Message] | None = Field(
        default=None,
        description="A list of messages that will begin the message list sent to the model"
        "The message content can be a Jinja2 template, in which case the input_variables_schema will be set"
        "to describe the variables used and the prompt will be rendered with the input variables before"
        "being sent to the model",
    )

    input_variables_schema: dict[str, Any] | None = Field(
        default=None,
        description="A JSON schema for the variables used to template the instructions during the inference."
        "Auto generated from the prompt if the prompt is a Jinja2 template",
    )
    output_schema: OutputSchema | None = Field(
        default=None,
        description="A JSON schema for the output of the model, aka the schema in the response format",
    )


class Error(BaseModel):
    error: str


class Input(BaseModel):
    """The input of the completion, composed of:
    - variables, that are used to template the prompt when the prompt is a template
    - messages, that are appended to the rendered (if needed) prompt

    When sending a list of messages to the completion endpoint, the messages are split into two parts:
    - the first system message if there is no template, or the messages up to the last templated user message
    are part extracted from the input and used as part of the version (version.prompt)
    - the remaining messages are part of input.messages

    For example, when sending
    ```
    openai.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert email summarizer. Analyze the email content "
                    "and provide a structured summary with key points, actions needed, "
                    "and deadlines. Extract all important information systematically."
                )
            },
            {
                "role": "user",
                "content": "Please summarize this email:\n\n{{ email_content }}"
            }
        ],
        extra_body={
            "input": {
                "variables": {
                    "email_content": "..."
                }
            }
        }
    ```

    The last templated message is the last user message, which means that:
    - version.prompt will contain the system and user messages
    - input.messages will be empty
    - input.variables with contain the email_content and will be used to render the user message
    """

    id: str = Field(
        default="",
        description="The id of the input. Auto generated.",
    )
    messages: list[Message] | None = Field(
        default=None,
        description="Optional, messages part of the conversation appended to the rendered (if needed) prompt",
    )
    variables: dict[str, Any] | None = Field(
        default=None,
        description="Optional, variables used to template the prompt when the prompt is a template",
    )


class Output(BaseModel):
    messages: list[Message] | None = Field(
        default=None,
        description="The messages sent to the model. This is the messages that are returned to the user. None if the inference failed.",
    )
    error: Error | None = Field(
        default=None,
        description="The error that occurred during the inference. None if the inference succeeded.",
    )


class Annotation(BaseModel):
    """An annotation to a completion or experiment. An annotation can be attached to a specific portion of the object
    it defines.

    Examples of targets:
    - an annotation for the first version of an experiment would define experiment_id=..., and key_path=versions.0
    - an annotation for a `name` inpit variable in a completion would define completion_id=..., and key_path=input.variables.name

    """

    id: str = Field(
        default="",
        description="The user defined id of the annotation. Auto generated if not provided.",
    )
    created_at: datetime = Field(
        default_factory=datetime_factory,
        description="The timestamp of the annotation creation. Auto generated",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="The timestamp of the annotation last update. Auto generated",
    )

    class Target(BaseModel):
        completion_id: str | None = Field(
            default=None,
            description="The unique identifier of the completion that the annotation is associated with, if any. "
            "At least one of completion_id or experiment_id must be present.",
        )
        experiment_id: str | None = Field(
            default=None,
            description="The unique identifier of the experiment that the annotation is associated with, if any. "
            "At least one of completion_id or experiment_id must be present.",
        )
        key_path: str | None = Field(
            default=None,
            description="A path to a specific field being annotated (e.g., 'input.sentiment'). Use None to annotate the entire target.",
        )

    target: Target | None = Field(
        default=None,
        description="The target of the annotation, meaning the object the annotation is associated with.",
    )

    class Context(BaseModel):
        experiment_id: str | None = None
        agent_id: str | None = None

    context: Context | None = Field(
        default=None,
        description="The context of the annotation, meaning information about where the annotation was added. "
        "For example, an annotation targeting a completion within an experiment would have target.completion_id and "
        "context.experiment_id set",
    )

    author_name: str = Field(
        description="The author of the annotation, defined by the client. E-g: 'Claude Code', 'John Doe', 'my_script.py',etc.",
    )

    text: str | None = Field(
        default=None,
        description="Text content of the annotation. For suggestions, may include GitHub-style ```suggestion blocks. At least one of text or metric must be present.",
    )

    # Here nesting makes it explicit that name and value are always present when metric is present
    class Metric(BaseModel):
        name: (
            # Metric names are only here as suggestions
            # The `| str` allows for custom metric names to be used
            Literal[
                "accuracy",
                "precision",
                "mse",
                "rmse",
                "mae",
                "time_to_first_token",
                "user_feedback",
            ]
            | str
        )
        value: float | str | bool

    metric: Metric | None = Field(
        default=None,
        description="Metric associated with the annotation. At least one of text or metric must be present.",
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Metadata associated with the annotation. Can be used to store additional information "
        "about the annotation.",
    )


class Completion(BaseModel):
    id: str
    agent_id: str

    version: Version = Field(
        description="The version of the model used for the inference.",
    )

    conversation_id: str | None = Field(
        default=None,
        description="The unique identifier of the conversation that the completion is associated with, if any. "
        "None if the completion is not part of a conversation.",
    )

    input: Input = Field(
        description="The input of the inference, combining the appended messages and the variables",
    )

    output: Output = Field(description="The output of the inference")

    messages: list[Message] = Field(
        description="The full list of message sent to the model, includes the messages in the version prompt "
        "(rendered with the input variables if needed), the appended messages and the messages returned by the model",
    )

    annotations: list[Annotation] | None = Field(
        description="Annotations associated with the completion and the completion only. Annotations added within the scope of an experiment are not included here.",
    )

    metadata: dict[str, Any] = Field(
        description="Metadata associated with the completion. Can be used to store additional information about the completion.",
    )

    cost_usd: float = Field(description="The cost of the inference in USD.")
    duration_seconds: float | None = Field(
        description="The duration of the inference in seconds.",
    )


class ExperimentItem(BaseModel):
    """A portion of an experiment, returned as part of a list of experiments.

    This is a lighter payload than the full experiment, and is used to display a list of experiments.
    """

    id: str
    created_at: datetime
    user_id: str
    title: str
    description: str
    result: str | None


class Experiment(BaseModel):
    id: str
    created_at: datetime
    author_name: str
    url: str

    title: str = Field(description="The title of the experiment.")
    description: str = Field(description="The description of the experiment.")
    result: str | None = Field(description="A user defined result of the experiment.")
    agent_id: str = Field(description="The agent that created the experiment.")

    class Completion(BaseModel):
        id: str
        # Only IDs are provided here but they have the same format as in the full object (completion.input.id)
        input: ModelWithID
        version: ModelWithID
        output: Output
        cost_usd: float
        duration_seconds: float

    completions: list[Completion] = Field(description="The completions of the experiment.")

    versions: list[Version]

    inputs: list[Input]

    annotations: list[Annotation] | None = Field(
        description="Annotations associated with the experiment, either tied to the experiment only or to a completion within the experiment.",
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Metadata associated with the experiment. Can be used to store additional information about the experiment.",
    )


class CreateExperimentRequest(BaseModel):
    id: str | None = None
    title: str
    description: str | None = None
    agent_id: str
    metadata: dict[str, Any] | None = None
    author_name: str


class PlaygroundOutput(BaseModel):
    class Completion(BaseModel):
        id: str
        output: Output
        cost_usd: float | None
        duration_seconds: float | None

    experiment_id: str
    experiment_url: str
    completions: list[Completion]


# ----------------------------------------
# Documentation


class SearchDocumentationResponse(BaseModel):
    page_content: str | None = Field(
        default=None,
        description="The content of the requested page, only present when a specific page is requested",
    )

    class QueryResult(BaseModel):
        content_snippet: str
        source_page: str

    query_results: list[QueryResult] | None = Field(
        default=None,
        description="Query results, only present when a query is provided",
    )


class SupportsModality(BaseModel):
    """Defines what modalities (input/output types) are supported by a model."""

    image: bool
    audio: bool
    pdf: bool
    text: bool


class ModelSupports(BaseModel):
    """Data about what the model supports on the WorkflowAI platform.

    Note that a single model might have different capabilities based on the provider.
    """

    input: SupportsModality = Field(
        description="Whether the model supports input of the given modality.",
    )
    output: SupportsModality = Field(
        description="""Whether the model supports output of the given modality.
        If false, the model will not return any output.""",
    )
    parallel_tool_calls: bool = Field(
        description="""Whether the model supports parallel tool calls, i.e. if the model can return multiple tool calls
        in a single inference. If the model does not support parallel tool calls, the parallel_tool_calls parameter
        will be ignored.""",
    )
    tools: bool = Field(
        description="""Whether the model supports tools. If false, the model will not support tool calling.
        Requests containing tools will be rejected.""",
    )
    top_p: bool = Field(
        description="Whether the model supports top_p. If false, the top_p parameter will be ignored.",
    )
    temperature: bool = Field(
        description="Whether the model supports temperature. If false, the temperature parameter will be ignored.",
    )


class ModelReasoning(BaseModel):
    """Configuration for reasoning capabilities of the model.

    A mapping from a reasoning effort (disabled, low, medium, high) to a
    reasoning token budget. The reasoning token budget represents the maximum number
    of tokens that can be used for reasoning.
    """

    can_be_disabled: bool = Field(
        description="Whether the reasoning can be disabled for the model.",
    )
    low_effort_reasoning_budget: int = Field(
        description="The maximum number of tokens that can be used for reasoning at low effort for the model.",
    )
    medium_effort_reasoning_budget: int = Field(
        description="The maximum number of tokens that can be used for reasoning at medium effort for the model.",
    )
    high_effort_reasoning_budget: int = Field(
        description="The maximum number of tokens that can be used for reasoning at high effort for the model.",
    )

    min_reasoning_budget: int = Field(
        description="The minimum number of tokens that can be used for reasoning for the model, without disabling reasoning.",
    )

    max_reasoning_budget: int = Field(
        description="The maximum number of tokens that can be used for reasoning for the model.",
    )


class ModelPricing(BaseModel):
    """Pricing information for model usage in USD per token."""

    input_token_usd: float = Field(
        description="Cost per input token in USD.",
    )
    output_token_usd: float = Field(
        description="Cost per output token in USD.",
    )


class ModelContextWindow(BaseModel):
    """Context window and output token limits for the model."""

    max_tokens: int = Field(
        description="""The maximum number of tokens that can be used for the context window for the model.
        Input and output combined.""",
    )
    max_output_tokens: int = Field(
        description="The maximum number of tokens that the model can output.",
    )


class Model(BaseModel):
    """Complete model information including capabilities, pricing, and metadata."""

    id: str = Field(
        description="Unique identifier for the model, which should be used in the `model` parameter of the OpenAI API.",
    )
    display_name: str = Field(
        description="Human-readable name for the model.",
    )
    icon_url: str = Field(
        description="URL to the model's icon image.",
    )

    supports: ModelSupports = Field(
        description="Detailed information about what the model supports.",
    )

    pricing: ModelPricing = Field(
        description="Pricing information for the model.",
    )

    release_date: date = Field(
        description="The date the model was released on the WorkflowAI platform.",
    )

    reasoning: ModelReasoning | None = Field(
        default=None,
        description="Reasoning configuration for the model. None if the model does not support reasoning.",
    )

    context_window: ModelContextWindow = Field(
        description="Context window and output token limits for the model.",
    )

    speed_index: float = Field(
        description="An indication of speed of the model, the higher the index, the faster the model. "
        "The index is calculated from the model's average tokens-per-second rate on a standardized translation task.",
    )


# ----------------------------------------
# Views


class TableGraph(BaseModel):
    """A table graph is a way to display a table of results."""

    type: Literal["table"] = "table"


class Axis(BaseModel):
    field: str
    unit: str | None = Field(default=None, description="The unit of the axis")
    label: str | None = Field(default=None, description="The label of the axis")


class ColoredAxis(Axis):
    color_hex: str | None = Field(default=None, examples=["#0f0"])


class BarGraph(BaseModel):
    """A bar graph is a way to display a bar chart of results.

    For example, an aggregation of cost by agent by date would produce rows like:

    | agent_id | date       | cost |
    |----------|------------|------|
    | agent_1  | 2021-01-01 | 100  |
    | agent_2  | 2021-01-01 | 200  |
    | agent_1  | 2021-01-02 | 150  |
    | agent_2  | 2021-01-02 | 250  |
    ...

    In this case:
    - the x axis would be "date"
    - the y axis would be "cost"
    Any other dimension would be used to create individual bars, in this case "agent_id".
    """

    type: Literal["bar"] = "bar"

    x: Axis
    y: list[ColoredAxis]
    stacked: bool = Field(default=False, description="Whether the bars should be stacked")


class LineGraph(BaseModel):
    """A line graph is a way to display line chart results.
    Similar to bar graphs but connects data points with lines.
    """

    type: Literal["line"] = "line"

    x: Axis
    y: list[ColoredAxis]


class PieGraph(BaseModel):
    """A pie graph is a way to display proportional data as segments of a circle.
    Each segment represents a category with its relative size based on the data value.
    """

    type: Literal["pie"] = "pie"

    x: Axis  # Category field
    y: list[ColoredAxis]  # Value field


class ScatterGraph(BaseModel):
    """A scatter graph plots individual data points in a two-dimensional space.
    Useful for showing relationships between two numeric variables.
    """

    type: Literal["scatter"] = "scatter"

    x: Axis  # X-axis numeric field
    y: list[ColoredAxis]  # Y-axis numeric field


Graph = Annotated[BarGraph | LineGraph | PieGraph | ScatterGraph | TableGraph, Field(discriminator="type")]


class View(BaseModel):
    """A view is essentially a SQL query that is executed on the completions table,
    paired with way to display the results.
    """

    id: str = Field(default="", description="Unique identifier for the view")
    title: str = Field(description="View title")
    query: str = Field(description="SQL query to filter/aggregate completions")

    graph: Graph | None = None


class ViewFolder(BaseModel):
    """A dashboard is a collection of views that are displayed together.
    A dashboard is always created with an empty section."""

    id: str = Field(default="", description="Unique identifier for the dashboard. Auto generated.")
    name: str = Field(description="View folder name")

    views: list[View] = Field(description="Views to display in the folder", default_factory=list)


class PatchViewFolderRequest(BaseModel):
    name: str | None = None


class CreateViewRequest(View):
    folder_id: str | None = Field(default=None, description="The section id the view belongs to")


class CreateViewResponse(BaseModel):
    id: str
    view_url: str


class PatchViewRequest(BaseModel):
    title: str | None = Field(default=None, description="View title")
    query: str | None = Field(default=None, description="SQL query to filter/aggregate completions")
    graph: Graph | None = Field(default=None, description="Graph to display in the view")
    position: int | None = Field(default=None, description="Position of the view in the section")
    folder_id: str | None = Field(default=None, description="A new folder id to move the view to")


# ----------------------------------------
# API Keys


class APIKey(BaseModel):
    id: str
    name: str
    partial_key: str
    created_at: datetime
    last_used_at: datetime | None
    created_by: str


class CompleteAPIKey(APIKey):
    key: str


class CreateAPIKeyRequest(BaseModel):
    name: str
    created_by: str = "user"


class QueryCompletionResponse(BaseModel):
    rows: list[dict[str, Any]]
    url: str


# ------------------------------------------------
# Deployments


class Deployment(BaseModel):
    """A deployment represents a specific model configuration for production use."""

    id: str = Field(
        description="A unique user provided ID for the deployment",
        examples=["my-agent-id:production#1"],
    )

    agent_id: str

    version: Version = Field(
        description="Version configuration including model, prompt, and tools",
    )
    created_at: datetime = Field(
        default_factory=datetime_factory,
        description="The timestamp when the deployment was created",
    )

    created_by: str

    updated_at: datetime | None = None

    metadata: dict[str, Any] | None = None

    url: str


class DeploymentCreate(BaseModel):
    version: Version
    metadata: dict[str, Any] | None = None
    created_by: str
    agent_id: str
    id: str


class DeploymentUpdate(BaseModel):
    version: Annotated[
        Version | None,
        Field(
            description="""A new version for the deployment. Note that it is only possible to update the version of a
        deployment when the new version expects a compatible variables (aka input_variables_schema) and response
        format types (aka output_schema). Schemas are considered compatible if the structure they describe are
        the same, i-e all fields have the same name, properties and types.""",
        ),
    ] = None

    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def post_validate(self):
        # check if at least one field is not None
        if not self.version and not self.metadata:
            raise ValueError("Either version or metadata must be provided")
        return self
