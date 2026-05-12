"""add template instances slug and status fields

Revision ID: 8b2cd72d3e5c
Revises: e3714af1afe9
Create Date: 2026-05-12 17:22:18.218289

"""

import sqlalchemy as sa

from alembic import op

revision: str = "8b2cd72d3e5c"
down_revision: str | None = "e3714af1afe9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# Helpers

# Keep the enum name in one place so upgrade() and downgrade() stay in sync.
_STATUS_ENUM_NAME = "template_instance_status"
_STATUS_VALUES = ("draft", "published", "archived")

# Build a reusable SA Enum object. create_type=False because we manage the
# CREATE / DROP TYPE statements explicitly via op.execute() for clarity and
# to avoid Alembic double-creating it on autogenerate round-trips.
status_enum = sa.Enum(
    *_STATUS_VALUES,
    name=_STATUS_ENUM_NAME,
)


def upgrade() -> None:

    # 1. Create the table.
    op.create_table(
        "template_instances",
        # Primary key — UUID v7 generated application-side.
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        # Owner — hard delete cascade keeps the DB clean.
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # ---------- publish-flow fields (the purpose of this ticket) ----------
        # Nullable until the instance is explicitly published.
        # Uniqueness is enforced by a dedicated index below (allows
        # multiple NULLs — standard SQL behaviour for unique indexes).
        sa.Column(
            "slug",
            sa.String(255),
            nullable=True,
        ),
        # status: every row is 'draft' until deliberately changed.
        # server_default covers inserts that bypass the ORM layer.
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="draft",
        ),
        # ---------- audit timestamps (best practice for new tables) ----------
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 2. Index on user_id for fast per-user queries.
    op.create_index(
        "ix_template_instances_user_id",
        "template_instances",
        ["user_id"],
    )

    # 3. Unique index on slug.
    #    Using a *partial* unique index (WHERE slug IS NOT NULL) is the
    #    idiomatic PostgreSQL approach: it enforces uniqueness only among
    #    non-null slugs, so multiple draft rows can coexist with slug=NULL
    #    without violating the constraint.
    op.execute(
        "CREATE UNIQUE INDEX uq_template_instances_slug "
        "ON template_instances (slug) "
        "WHERE slug IS NOT NULL"
    )


# downgrade — clean rollback, no data loss risk (table is dropped entirely)


def downgrade() -> None:
    # Drop the table (and implicitly its indexes and FK constraints).
    op.drop_table("template_instances")

    # Drop the enum type.  Must happen after the table is gone because
    # PostgreSQL will refuse to drop a type that is still in use.
    op.execute(f"DROP TYPE IF EXISTS {_STATUS_ENUM_NAME}")
