from fastapi import APIRouter, status

from app.api.deps import DBSession
from app.schemas.layout import LayoutResponse
from app.schemas.response import SuccessResponse
from app.services.layout_service import list_layouts

router = APIRouter()


@router.get(
    "/layouts",
    response_model=SuccessResponse[list[LayoutResponse]],
    status_code=status.HTTP_200_OK,
    summary="Fetch available badge layouts",
    description="Returns all layout options an organiser can choose from.",
    responses={
        500: {"description": "Internal server error"},
    },
)
async def fetch_layouts(db: DBSession) -> SuccessResponse[list[LayoutResponse]]:
    layouts = await list_layouts(db)
    return SuccessResponse(
        message="Layouts fetched successfully.",
        data=layouts,
    )
