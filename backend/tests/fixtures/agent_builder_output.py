"""A complex type that can be used to test the schema sanitation"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class URLStatus(str, Enum):
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"


class URLContent(BaseModel):
    url: str = Field(description="The URL of the content")
    content: str | None = Field(default=None, description="The content of the URL if reachable")
    status: URLStatus = Field(
        default=URLStatus.REACHABLE,
        description="The status of the URL: reachable or unreachable",
    )


class ChatMessage(BaseModel):
    role: Literal["USER", "ASSISTANT"] = Field(
        description="The role of the message sender",
    )
    content: str = Field(
        description="The content of the message",
        examples=[
            "Thank you for your help!",
            "What is the weather forecast for tomorrow?",
        ],
    )


class Product(BaseModel):
    name: str | None = None
    features: list[str] | None = None
    description: str | None = None
    target_users: list[str] | None = None


class AgentSchemaJson(BaseModel):
    agent_name: str = Field(description="The name of the agent in Title Case")
    input_json_schema: dict[str, Any] | None = Field(
        default=None,
        description="The JSON schema of the agent input",
    )
    output_json_schema: dict[str, Any] | None = Field(
        default=None,
        description="The JSON schema of the agent output",
    )


type InputFieldType = (
    "InputGenericFieldConfig | EnumFieldConfig | InputArrayFieldConfig | InputObjectFieldConfig | None"
)
type OutputFieldType = "OutputGenericFieldConfig | OutputStringFieldConfig | EnumFieldConfig | OutputArrayFieldConfig | OutputObjectFieldConfig | None"
type InputItemType = "EnumFieldConfig | InputObjectFieldConfig | InputGenericFieldConfig | None"
type OutputItemType = (
    "OutputStringFieldConfig | EnumFieldConfig | OutputObjectFieldConfig | OutputGenericFieldConfig | None"
)


class InputSchemaFieldType(Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    AUDIO_FILE = "audio_file"
    IMAGE_FILE = "image_file"
    DOCUMENT_FILE = "document_file"  # Include various text formats, pdfs and images
    DATE = "date"
    DATETIME = "datetime"
    TIMEZONE = "timezone"
    URL = "url"
    EMAIL = "email"
    HTML = "html"


class OutputSchemaFieldType(Enum):
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    DATETIME_LOCAL = "datetime_local"
    TIMEZONE = "timezone"
    URL = "url"
    EMAIL = "email"
    HTML = "html"
    IMAGE_FILE = "image_file"


class BaseFieldConfig(BaseModel):
    name: str | None = Field(
        default=None,
        description="The name of the field, must be filled when the field is an object field",
    )
    description: str | None = Field(default=None, description="The description of the field")


class InputGenericFieldConfig(BaseFieldConfig):
    type: InputSchemaFieldType | None = Field(default=None, description="The type of the field")


class OutputStringFieldConfig(BaseFieldConfig):
    type: Literal["string"] = "string"
    examples: list[str] | None = Field(default=None, description="The examples of the field")


class EnumFieldConfig(BaseFieldConfig):
    type: Literal["enum"] = "enum"
    values: list[str] | None = Field(default=None, description="The possible values of the enum")


class InputObjectFieldConfig(BaseFieldConfig):
    type: Literal["object"] = "object"
    fields: list[InputFieldType] = Field(description="The fields of the object", default_factory=list)


class InputArrayFieldConfig(BaseFieldConfig):
    type: Literal["array"] = "array"
    items: InputItemType = Field(default=None, description="The type of the items in the array")


class OutputGenericFieldConfig(BaseFieldConfig):
    type: OutputSchemaFieldType | None = Field(default=None, description="The type of the field")


class OutputObjectFieldConfig(BaseFieldConfig):
    type: Literal["object"] = "object"
    fields: list[OutputFieldType] = Field(description="The fields of the object", default_factory=list)


class OutputArrayFieldConfig(BaseFieldConfig):
    type: Literal["array"] = "array"
    items: OutputItemType = Field(default=None, description="The type of the items in the array")


class ChatMessageWithExtractedURLContent(ChatMessage):
    extracted_url_content: list[URLContent] | None = Field(
        default=None,
        description="The content of the URLs contained in 'content', if any",
    )


class AgentBuilderInput(BaseModel):
    previous_messages: list[ChatMessage] = Field(
        description="List of previous messages exchanged between the user and the assistant",
    )
    new_message: ChatMessageWithExtractedURLContent = Field(
        description="The new message received from the user, based on which the routing decision is made",
    )
    existing_agent_schema: AgentSchemaJson | None = Field(
        default=None,
        description="The previous agent schema, to update, if any",
    )
    available_tools_description: str | None = Field(
        default=None,
        description="The description of the available tools, potentially available for the agent we are generating the schema for",
    )

    class UserContent(BaseModel):
        company_name: str | None = None
        company_description: str | None = None
        company_locations: list[str] | None = None
        company_industries: list[str] | None = None
        company_products: list[Product] | None = None
        current_agents: list[str] | None = Field(
            default=None,
            description="The list of existing agents for the company",
        )

    user_context: UserContent | None = Field(
        default=None,
        description="The context of the user, to inform the decision about the new agents schema",
    )


class AgentSchema(BaseModel):
    agent_name: str = Field(description="The name of the agent in Title Case", default="")
    input_schema: InputObjectFieldConfig | None = Field(description="The schema of the agent input", default=None)
    output_schema: OutputObjectFieldConfig | None = Field(description="The schema of the agent output", default=None)


class AgentBuilderOutput(BaseModel):
    answer_to_user: str = Field(description="The answer to the user, after processing of the 'new_message'", default="")

    new_agent_schema: AgentSchema | None = Field(
        description="The new agent schema, if any, after processing of the 'new_message'",
        default=None,
    )
