import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    PlatformTemplateNotFoundError,
    TemplateInstanceForbiddenError,
    TemplateInstanceNotFoundError,
)
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
        select(OrganiserTemplate).where(OrganiserTemplate.id == instance_id)
    )
    instance = result.scalars().first()

    if instance is None:
        raise TemplateInstanceNotFoundError

    if instance.organizer_id != organizer_id:
        raise TemplateInstanceForbiddenError

    # Delete the existing logo from Cloudinary before uploading the new one.
    if instance.logo_public_id:
        await delete_logo(instance.logo_public_id)

    logo_url, public_id = await upload_logo(image_data)

    instance.logo_url = logo_url
    instance.logo_public_id = public_id
    await session.commit()
    await session.refresh(instance)

    logger.info(
        "Uploaded logo for template instance %s (public_id=%s)",
        instance_id,
        public_id,
    )
    return logo_url
