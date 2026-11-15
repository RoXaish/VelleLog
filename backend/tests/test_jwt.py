from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.core.tokens import create_access_token, decode_access_token


def test_access_token_contains_subject_and_expiration() -> None:
    token = create_access_token(subject=42)

    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert isinstance(payload["exp"], int)
    assert datetime.fromtimestamp(payload["exp"], tz=timezone.utc) > datetime.now(
        timezone.utc
    )


def test_access_token_uses_configured_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 5)

    payload = decode_access_token(create_access_token(subject=1))

    assert payload["exp"] - payload["iat"] == 300


def test_expired_token_is_rejected() -> None:
    token = create_access_token(subject=1, expires_delta=timedelta(seconds=-1))

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("not-a-valid-jwt")


def test_token_without_expiration_claim_is_rejected() -> None:
    token = jwt.encode(
        {"sub": "1"},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_token_signed_with_unknown_secret_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "attacker-controlled-secret-value-32-chars",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_signing_secret_is_configuration_driven(monkeypatch: pytest.MonkeyPatch) -> None:
    token = create_access_token(subject=7)
    assert decode_access_token(token)["sub"] == "7"

    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        SecretStr("alternate-test-signing-secret-value-32-chars"),
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)

    new_token = create_access_token(subject=7)
    assert decode_access_token(new_token)["sub"] == "7"
