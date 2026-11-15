from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"


def create_access_token(
    subject: int | str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    The subject is the user ID, and the token always includes issued-at and
    expiration timestamps. Expiration defaults to the configured lifetime.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Validate a JWT's signature and required claims, including expiration.

    Raises ``jwt.InvalidTokenError`` (or a subclass such as
    ``ExpiredSignatureError``) when the token cannot be trusted.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
