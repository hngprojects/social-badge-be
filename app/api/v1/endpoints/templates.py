from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import (
    PlatformTemplateNotFoundError,
    TemplateInstanceForbiddenError,
    TemplateInstanceNotFoundError,
)
from app.core.rate_limit import limiter
from app.schemas.response import ErrorResponse, SuccessResponse
from app.schemas.template import (
    CreateTemplateInstanceRequest,
    LogoUploadResponse,
    TemplateInstanceResponse,
)
from app.services.template_service import create_template_instance, upload_template_logo

router = APIRouter()

_MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB
_ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg"}


@router.post(
    "/instances",
    response_model=SuccessResponse[TemplateInstanceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new template instance from a platform template",
    description=(
        "Creates a new organiser template instance linked to the chosen "
        "platform template. The original platform template is never modified. "
        "The organiser is taken from the JWT, never from the request body."
    ),
    responses={
        201: {
            "description": "Template instance created.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Template instance created successfully.",
                        "data": {
                            "instance_id": "019e1b66-c4ec-7b80-8c85-84c2fe4f9c84",
                            "platform_template_id": (
                                "019e1b66-c4ec-7b80-8c85-84c2fe4f9c00"
                            ),
                            "organizer_id": "019e1b66-c4ec-7b80-8c85-84c2fe4f9c11",
                            "created_at": "2026-05-12T09:30:00Z",
                        },
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Unauthenticated."},
        404: {"model": ErrorResponse, "description": "Platform template not found."},
        422: {"model": ErrorResponse, "description": "Validation error."},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded."},
    },
)
@limiter.limit("30/minute")
async def create_instance(
    request: Request,
    session: DBSession,
    current_user: CurrentUser,
    payload: CreateTemplateInstanceRequest,
) -> SuccessResponse[TemplateInstanceResponse]:
    """Create a new organiser template instance from a platform template."""
    try:
        instance = await create_template_instance(
            session=session,
            organizer_id=current_user.id,
            platform_template_id=payload.platform_template_id,
        )
    except PlatformTemplateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform template not found.",
        ) from exc

    assert instance.created_at is not None  # noqa: S101
    return SuccessResponse(
        message="Template instance created successfully.",
        data=TemplateInstanceResponse(
            instance_id=instance.id,
            platform_template_id=instance.platform_template_id,
            organizer_id=instance.organizer_id,
            created_at=instance.created_at,
        ),
    )


@router.put(
    "/instances/{instance_id}/logo",
    response_model=SuccessResponse[LogoUploadResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload a logo for a template instance",
    description=(
        "Accepts a multipart/form-data upload with a single PNG or JPG image "
        "(max 2 MB). Stores the file in Cloudinary under the template-logos/ "
        "folder and returns the resulting URL. If the instance already has a "
        "logo the old file is deleted from Cloudinary first. "
        "The instance must belong to the authenticated organiser."
    ),
    responses={
        200: {
            "description": "Logo uploaded successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Logo uploaded successfully.",
                        "data": {
                            "logo_url": "https://res.cloudinary.com/demo/image/upload/template-logos/abc.png"
                        },
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Unauthenticated."},
        403: {
            "model": ErrorResponse,
            "description": "Instance belongs to another organiser.",
        },
        404: {"model": ErrorResponse, "description": "Template instance not found."},
        413: {"model": ErrorResponse, "description": "File exceeds the 2 MB limit."},
        415: {
            "model": ErrorResponse,
            "description": "Unsupported file type (PNG and JPG only).",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded."},
    },
)
@limiter.limit("10/minute")
async def upload_logo(
    instance_id: UUID,
    request: Request,
    session: DBSession,
    current_user: CurrentUser,
    file: UploadFile,
) -> SuccessResponse[LogoUploadResponse]:
    """Upload or replace the logo for a template instance."""
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Only PNG and JPG images are allowed.",
        )

    image_data = await file.read()
    if len(image_data) > _MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size exceeds the 2 MB limit.",
        )

    try:
        logo_url = await upload_template_logo(
            session=session,
            instance_id=instance_id,
            organizer_id=current_user.id,
            image_data=image_data,
        )
    except TemplateInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template instance not found.",
        ) from exc
    except TemplateInstanceForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this template instance.",
        ) from exc

    return SuccessResponse(
        message="Logo uploaded successfully.",
        data=LogoUploadResponse(logo_url=logo_url),
    )
