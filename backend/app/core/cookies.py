import secrets

from fastapi import Response

from app.core.config import settings

AUTH_COOKIE_NAME = "velle_access_token"
CSRF_COOKIE_NAME = "velle_csrf_token"
AUTH_COOKIE_PATH = "/api"
CSRF_COOKIE_PATH = "/"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _cookie_max_age() -> int:
    return settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


def set_auth_cookies(
    response: Response,
    access_token: str,
    csrf_token: str,
) -> None:
    """Set the HttpOnly access cookie and its JS-readable CSRF companion."""
    max_age = _cookie_max_age()
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=max_age,
        path=AUTH_COOKIE_PATH,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        path=CSRF_COOKIE_PATH,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path=CSRF_COOKIE_PATH,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )
