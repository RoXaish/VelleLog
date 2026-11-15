from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Velle Log - Coordination platform for friend groups.",
    version="0.1.0",
)

# Register API routes under /api prefix
app.include_router(api_router, prefix="/api")
