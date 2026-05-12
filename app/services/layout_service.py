from sqlalchemy import select

from app.api.deps import DBSession
from app.models.platform_template import PlatformTemplate
from app.schemas.layout import LayoutResponse


async def list_layouts(db: DBSession) -> list[LayoutResponse]:
    """Return all supported template layout options from the database."""
    result = await db.execute(
        select(PlatformTemplate)
        .where(PlatformTemplate.is_active)
        .order_by(PlatformTemplate.title)
    )
    templates = result.scalars().all()

    return [
        LayoutResponse(
            id=template.id,
            name=template.title,
            description=template.description,
            preview_image_url=template.preview_image_url,
        )
        for template in templates
    ]
