from fastapi import APIRouter
from app.api.routes import auth, busy_blocks, groups, health

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(groups.router)
api_router.include_router(busy_blocks.router)
api_router.include_router(health.router, tags=["health"])
