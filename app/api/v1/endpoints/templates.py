from typing import Any
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.api.deps import CurrentUser, DBSession
from app.models.organiser_template import OrganiserTemplate
from app.schemas.templates import TemplateInstanceFull, TemplateInstanceSummary
from app.schemas.response import SuccessResponse
import uuid

router = APIRouter()


@router.get(
    "/instances",
    response_model=SuccessResponse[list[TemplateInstanceSummary]],
    status_code=status.HTTP_200_OK,
    summary="Get all template instances for the authenticated organiser",
    responses={
        200: {"description": "List of template instances (empty array if none)"},
        401: {"description": "Missing or invalid token"},
    },
)
async def get_template_instances(
    session: DBSession,
    current_user: CurrentUser,
) -> Any:
    result = await session.execute(
        select(OrganiserTemplate)
        .where(
            OrganiserTemplate.organiser_id == current_user.id,
            OrganiserTemplate.deleted_at.is_(None),
        )
    )
    instances = result.scalars().all()

    return SuccessResponse(
        message="Template instances retrieved successfully",
        data=[TemplateInstanceSummary.from_orm_row(i) for i in instances],
    )


@router.get(
    "/instances/{instance_id}",
    response_model=SuccessResponse[TemplateInstanceFull],
    status_code=status.HTTP_200_OK,
    summary="Get full configuration for a single template instance",
    responses={
        200: {"description": "Full template instance configuration"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Instance does not belong to authenticated organiser"},
        404: {"description": "Instance not found"},
    },
)
async def get_template_instance(
    instance_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> Any:
    result = await session.execute(
        select(OrganiserTemplate)
        .where(
            OrganiserTemplate.id == instance_id,
            OrganiserTemplate.deleted_at.is_(None),
        )
    )
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template instance not found",
        )

    if instance.organiser_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template instance",
        )

    return SuccessResponse(
        message="Template instance retrieved successfully",
        data=TemplateInstanceFull.from_orm_row(instance),
    )