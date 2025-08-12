from pydantic import BaseModel, Field


class Typology(BaseModel):
    has_text: bool = Field(default=True, description="Whether the schema contains text")
    has_image: bool = Field(default=False, description="Whether the schema contains an image")
    has_audio: bool = Field(default=False, description="Whether the schema contains an audio")
    has_pdf: bool = Field(default=False, description="Whether the schema contains a pdf")
    has_tools: bool = Field(default=False, description="Whether the schema contains tools")


class IOTypology(BaseModel):
    input: Typology
    output: Typology = Field(default_factory=Typology)
