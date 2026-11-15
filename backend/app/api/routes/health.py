from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health Check")
def health_check() -> dict[str, str]:
    """
    Health check endpoint returning application status.
    Accessible without authentication.
    """
    return {"status": "ok"}
