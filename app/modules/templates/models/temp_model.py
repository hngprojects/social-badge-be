import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB as jsonb, UUID
from uuid_utils import uuid7

from app.models.base import Base
from app.models.user import User

class TempModel(Base):
    __tablename__ = "organiser_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7, unique=True, index=True)
    # Foreign Key to the 'users' table
    organiser_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    platform_template_id: Mapped[str] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    canvas_data: Mapped[dict] = mapped_column(jsonb, nullable=False)
    default_caption: Mapped[str] = mapped_column(String(255), nullable=True)
    destination_link: Mapped[str] = mapped_column(String(255), nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(String(255), nullable=True)
    access_type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    share_slug: Mapped[str] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    organiser: Mapped["User"] = relationship("User", back_populates="templates")