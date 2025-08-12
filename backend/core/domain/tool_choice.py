from typing import Literal

from pydantic import BaseModel


class ToolChoiceFunction(BaseModel):
    name: str


type ToolChoice = Literal["auto", "none", "required"] | ToolChoiceFunction
