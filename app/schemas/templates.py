import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class TemplateInstanceSummary(BaseModel):
    instance_id: uuid.UUID
    event_name: str
    layout_thumbnail_url: str | None
    is_published: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_row(cls, row: Any) -> "TemplateInstanceSummary":
        return cls(
            instance_id=row.id,
            event_name=row.title,
            layout_thumbnail_url=row.thumbnail_url,
            is_published=row.is_published,
            updated_at=row.updated_at,
        )

class TemplateInstanceFull(BaseModel):
    instance_id: uuid.UUID
    organiser_id: uuid.UUID
    platform_template_id: uuid.UUID | None
    event_name: str
    canvas_data: dict | None
    default_caption: str | None
    destination_link: str | None
    thumbnail_url: str | None
    access_type: int | None
    is_published: bool
    published_at: datetime | None
    share_slug: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_row(cls, row: Any) -> "TemplateInstanceFull":
        return cls(
            instance_id=row.id,
            organiser_id=row.organiser_id,
            platform_template_id=row.platform_template_id,
            event_name=row.title,
            canvas_data=row.canvas_data,
            default_caption=row.default_caption,
            destination_link=row.destination_link,
            thumbnail_url=row.thumbnail_url,
            access_type=row.access_type,
            is_published=row.is_published,
            published_at=row.published_at,
            share_slug=row.share_slug,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )