import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, DateTime, Integer, Text, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7
from app.models.base import Base

class OrganiserTemplate(Base):
    __tablename__ = "organiser_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    organiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    platform_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    canvas_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    share_slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())