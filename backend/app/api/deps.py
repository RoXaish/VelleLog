import secrets
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.cookies import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME
from app.core.tokens import decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)
CSRF_HEADER_NAME = "X-CSRF-Token"


def _unauthorized() -> HTTPException:
    """Build the single generic authentication failure used by this module."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _csrf_forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="CSRF token validation failed",
    )


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str, str]:
    """
    Return the access token and its source.

    An explicit Authorization header takes precedence over the browser cookie.
    If that header is present but not a valid Bearer credential, the request is
    rejected rather than silently falling back to the cookie.
    """
    if request.headers.get("Authorization") is not None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise _unauthorized()
        return credentials.credentials, "bearer"

    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if not cookie_token:
        raise _unauthorized()
    return cookie_token, "cookie"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from a Bearer token or auth cookie.

    Missing, malformed, expired, or untrusted tokens and tokens whose subject
    no longer maps to a user all produce the same generic 401 response.
    """
    token, source = _extract_token(request, credentials)

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise _unauthorized() from None

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()

    request.state.auth_source = source
    return user


def verify_csrf(request: Request) -> None:
    """Validate the double-submit CSRF header against its cookie."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        raise _csrf_forbidden()


def require_csrf(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    """Authenticate a request and require CSRF proof when using cookie auth."""
    if getattr(request.state, "auth_source", None) == "cookie":
        verify_csrf(request)
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
CsrfProtectedUser = Annotated[User, Depends(require_csrf)]
