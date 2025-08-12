from pydantic import BaseModel, Field


class SourcedBaseModel(BaseModel):
    source: str = Field(description="The source of the data contained in the model")
