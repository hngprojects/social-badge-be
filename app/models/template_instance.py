import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TemplateInstanceStatus(enum.StrEnum):
    """Lifecycle states for a template instance in the publish flow."""

    draft = "draft"
    published = "published"
    archived = "archived"


class TemplateInstance(Base):
    """A user's instance of a badge template.

    slug is populated when the instance is published and must be unique
    across the table. It is intentionally nullable so that draft records
    can exist before any slug is assigned.

    status defaults to 'draft' for both new Python-side inserts *and*
    raw SQL inserts (server_default), keeping existing rows safe when
    this migration runs on a non-empty database.
    """

    __tablename__ = "template_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Publish-flow fields (the focus of this ticket)

    slug: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,  # null until the instance is published
        unique=True,  # enforced by uq_template_instances_slug below
        index=True,  # fast lookup by public URL
    )
    status: Mapped[TemplateInstanceStatus] = mapped_column(
        Enum(
            TemplateInstanceStatus,
            name="template_instance_status",
            create_type=True,  # Alembic will emit CREATE TYPE … in upgrade()
        ),
        nullable=False,
        default=TemplateInstanceStatus.draft,  # Python-side default
        server_default=TemplateInstanceStatus.draft.value,  # DB-side default
    )

    # Audit timestamps

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships

    user: Mapped["User"] = relationship(back_populates="template_instances")
