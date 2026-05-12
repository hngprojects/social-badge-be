from pydantic import BaseModel, Field


class LayoutResponse(BaseModel):
    """Layout option returned to organisers for template selection."""

    id: str = Field(..., description="Stable layout identifier", examples=["classic"])
    name: str = Field(..., description="Human-readable layout name")
    description: str = Field(..., description="Short description shown in UI")
    preview_image_url: str = Field(
        ...,
        description="Public URL for layout preview artwork",
    )
