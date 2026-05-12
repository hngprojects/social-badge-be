from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlatformTemplate(Base):
    """Platform-owned badge template layouts."""

    __tablename__ = "platform_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )  # UUID as string for compatibility
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    canvas_data: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON data for layout
    thumbnail_url: Mapped[str] = mapped_column(String(512), nullable=False)
    preview_image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
