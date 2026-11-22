from fastapi import APIRouter
from app.api.routes import (
    auth,
    busy_blocks,
    dashboard,
    groups,
    health,
    journal_entries,
    schedule_exceptions,
    tags,
    templates,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(journal_entries.router)
api_router.include_router(tags.router)
api_router.include_router(groups.router)
api_router.include_router(busy_blocks.router)
api_router.include_router(schedule_exceptions.router)
api_router.include_router(templates.router)
api_router.include_router(health.router, tags=["health"])
