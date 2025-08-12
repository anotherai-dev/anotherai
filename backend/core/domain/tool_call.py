from typing import Any

from pydantic import BaseModel, Field, model_validator

from core.utils.hash import hash_object
from core.utils.previews import compute_preview


class ToolCallRequest(BaseModel):
    id: str = Field(default="", description="The id of the tool call")

    index: int = 0
    tool_name: str
    tool_input_dict: dict[str, Any]

    @property
    def input_preview(self):
        return compute_preview(self.tool_input_dict)

    @property
    def preview(self):
        input_dict_preview = [f"{k}: {compute_preview(v, max_len=30)}" for k, v in self.tool_input_dict.items()]
        return f"{self.tool_name}({', '.join(input_dict_preview)})"

    @classmethod
    def default_id(cls, tool_name: str, input_dict: dict[str, Any]) -> str:
        return f"{tool_name}_{hash_object(input_dict)}"

    @model_validator(mode="after")
    def post_validate(self):
        if not self.id:
            self.id = self.default_id(self.tool_name, self.tool_input_dict)
        return self


class ToolCallResult(ToolCallRequest):
    id: str = Field(default="", description="The id of the tool call")
    result: Any = Field(default=None, description="The result of the tool call")
    error: str | None = Field(default=None, description="The error that occurred during the tool call if any")

    @property
    def output_preview(self):
        if self.error is not None:
            return f"Error: {self.error}"
        return compute_preview(self.result)

    def stringified_result(self):
        if self.error is not None:
            return f"Error: {self.error}"
        return str(self.result)
