from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, layouts

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(layouts.router, tags=["layouts"])
