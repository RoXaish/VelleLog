from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Velle Log - Coordination platform for friend groups.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Preserve FastAPI's standard validation error shape while redacting
    submitted passwords so they are never echoed back in a 422 response.
    """
    errors = []
    for error in exc.errors():
        sanitized_error = dict(error)
        if "password" in sanitized_error.get("loc", ()):
            sanitized_error.pop("input", None)
        errors.append(sanitized_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(errors)},
    )


# Register API routes under /api prefix
app.include_router(api_router, prefix="/api")
