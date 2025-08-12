from typing import Literal

from pydantic import BaseModel, Field

from core.domain.file import File

type ImageShape = Literal["square", "portrait", "landscape"]
type ImageFormat = Literal["png", "jpeg", "webp"]
type ImageBackground = Literal["opaque", "transparent", "auto"]
type ImageQuality = Literal["low", "medium", "high"]


class ImageOptions(BaseModel):
    """An extra field to specify image parameters"""

    quality: ImageQuality = "high"
    mask: File | None = None
    background: ImageBackground = "auto"
    format: ImageFormat = "png"
    shape: ImageShape = "square"
    image_count: int | None = Field(
        default=None,
        description="The number of images to generate. By default the number of images depends on the number "
        "of image fields in the output schema",
    )

    def __str__(self) -> str:
        components = [
            f"Generate {self.image_count} images",
            f"with the shape {self.shape}",
            f"and {self.format} format",
        ]
        if self.background != "auto":
            components.append(f"The background should be {self.background}")
        return " ".join(components)
