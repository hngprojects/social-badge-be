import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotTemplateOwnerError,
    OrganiserTemplateNotFoundError,
    PlatformTemplateNotFoundError,
    TemplateAlreadyPublishedError,
    TemplateInstanceForbiddenError,
    TemplateInstanceNotFoundError,
)
from app.core.slug import generate_share_slug
from app.models import OrganiserTemplate, PlatformTemplate
from app.services.cloudinary_service import delete_logo, upload_logo

logger = logging.getLogger(__name__)


async def create_template_instance(
    session: AsyncSession,
    organizer_id: UUID,
    platform_template_id: UUID,
) -> OrganiserTemplate:
    """Create a new organiser template instance from a platform template.

    The platform template itself is read-only and never modified.
    Title and canvas_data are copied from the platform template so the
    new instance has sensible defaults.
    """
    result = await session.execute(
        select(PlatformTemplate).where(PlatformTemplate.id == platform_template_id)
    )
    platform_template = result.scalars().first()
    if platform_template is None:
        raise PlatformTemplateNotFoundError

    instance = OrganiserTemplate(
        organizer_id=organizer_id,
        platform_template_id=platform_template_id,
        title=platform_template.title,
        canvas_data=platform_template.canvas_data or {},
    )
    session.add(instance)
    await session.flush()
    await session.commit()
    await session.refresh(instance)

    logger.info(
        "Created template instance %s for organiser %s",
        instance.id,
        organizer_id,
    )
    return instance


MAX_SLUG_RETRIES = 5


async def publish_template(
    session: AsyncSession,
    organizer_id: UUID,
    template_id: UUID,
) -> OrganiserTemplate:
    """Publish an organiser template.

    Sets is_published=True, sets published_at, and generates a unique
    share_slug if the template doesn't already have one. Idempotent on
    slug: republishing keeps the same slug.
    """
    result = await session.execute(
        select(OrganiserTemplate).where(OrganiserTemplate.id == template_id)
    )
    template = result.scalars().first()
    if template is None or template.deleted_at is not None:
        raise OrganiserTemplateNotFoundError
    if template.organizer_id != organizer_id:
        raise NotTemplateOwnerError
    if template.is_published:
        raise TemplateAlreadyPublishedError

    template.is_published = True
    template.published_at = datetime.now(UTC)

    if template.share_slug is None:
        for _ in range(MAX_SLUG_RETRIES):
            template.share_slug = generate_share_slug()
            try:
                await session.flush()
                break
            except IntegrityError:
                await session.rollback()
                template.share_slug = None
                continue
        else:
            raise RuntimeError("Could not generate a unique share slug")

    await session.commit()
    await session.refresh(template)

    logger.info("Published template %s by organiser %s", template.id, organizer_id)
    return template


async def unpublish_template(
    session: AsyncSession,
    organizer_id: UUID,
    template_id: UUID,
) -> OrganiserTemplate:
    """Unpublish an organiser template.

    Sets is_published=False. The share_slug is preserved so re-publishing
    later keeps the same URL.
    """
    result = await session.execute(
        select(OrganiserTemplate).where(OrganiserTemplate.id == template_id)
    )
    template = result.scalars().first()
    if template is None or template.deleted_at is not None:
        raise OrganiserTemplateNotFoundError
    if template.organizer_id != organizer_id:
        raise NotTemplateOwnerError

    template.is_published = False
    await session.commit()
    await session.refresh(template)

    logger.info("Unpublished template %s by organiser %s", template.id, organizer_id)
    return template


async def upload_template_logo(
    session: AsyncSession,
    instance_id: UUID,
    organizer_id: UUID,
    image_data: bytes,
) -> str:
    """Upload a logo for a template instance and return the Cloudinary URL.

    Raises:
        TemplateInstanceNotFoundError: if the instance does not exist.
        TemplateInstanceForbiddenError: if the instance belongs to another organiser.
        CloudinaryUploadError: if the Cloudinary upload fails.
    """
    result = await session.execute(
        select(OrganiserTemplate).where(
            OrganiserTemplate.id == instance_id,
            OrganiserTemplate.deleted_at.is_(None),
        )
    )
    instance = result.scalars().first()

    if instance is None:
        raise TemplateInstanceNotFoundError

    if instance.organizer_id != organizer_id:
        raise TemplateInstanceForbiddenError

    old_public_id = instance.logo_public_id

    # Upload first so the DB always points at a live asset.
    logo_url, public_id = await upload_logo(image_data)

    instance.logo_url = logo_url
    instance.logo_public_id = public_id
    try:
        await session.commit()
    except Exception:
        # DB commit failed — remove the just-uploaded asset to avoid orphans.
        await delete_logo(public_id)
        raise
    await session.refresh(instance)

    # Only delete the old asset after the DB is consistent.
    if old_public_id:
        await delete_logo(old_public_id)

    logger.info(
        "Uploaded logo for template instance %s (public_id=%s)",
        instance_id,
        public_id,
    )
    return logo_url
