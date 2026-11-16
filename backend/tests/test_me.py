from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.tokens import create_access_token, decode_access_token

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
ME_URL = "/api/auth/me"
RAW_PASSWORD = "s3cure-passphrase"
UNAUTHORIZED_DETAIL = {"detail": "Could not validate credentials"}
PUBLIC_FIELDS = {"id", "email", "created_at", "updated_at"}


def register_and_login(
    client: TestClient,
    email: str = "alex@example.com",
    password: str = RAW_PASSWORD,
) -> tuple[dict, str]:
    registered = client.post(
        REGISTER_URL,
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201

    logged_in = client.post(
        LOGIN_URL,
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200

    return registered.json(), logged_in.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_unauthorized(response) -> None:
    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED_DETAIL
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_current_user(client: TestClient, db_session: Session) -> None:
    user, token = register_and_login(client)

    response = client.get(ME_URL, headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PUBLIC_FIELDS
    assert body["id"] == user["id"]
    assert body["email"] == "alex@example.com"


def test_me_user_matches_token_subject(client: TestClient, db_session: Session) -> None:
    user, token = register_and_login(client)

    response = client.get(ME_URL, headers=auth_header(token))

    payload = decode_access_token(token)
    assert payload["sub"] == str(user["id"])
    assert response.json()["id"] == int(payload["sub"])


def test_me_missing_token_returns_401(client: TestClient, db_session: Session) -> None:
    register_and_login(client)
    client.cookies.clear()

    assert_unauthorized(client.get(ME_URL))


def test_me_malformed_token_returns_401(
    client: TestClient, db_session: Session
) -> None:
    register_and_login(client)

    assert_unauthorized(
        client.get(ME_URL, headers=auth_header("definitely-not-a-jwt"))
    )


def test_me_expired_token_returns_401(client: TestClient, db_session: Session) -> None:
    user, _ = register_and_login(client)
    expired_token = create_access_token(
        subject=user["id"],
        expires_delta=timedelta(seconds=-1),
    )

    assert_unauthorized(client.get(ME_URL, headers=auth_header(expired_token)))


def test_me_tampered_signature_returns_401(
    client: TestClient, db_session: Session
) -> None:
    user, _ = register_and_login(client)
    tampered_token = jwt.encode(
        {
            "sub": str(user["id"]),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "tampered-signature-secret-value-32-chars",
        algorithm="HS256",
    )

    assert_unauthorized(client.get(ME_URL, headers=auth_header(tampered_token)))


def test_me_nonexistent_user_returns_401(
    client: TestClient, db_session: Session
) -> None:
    user, _ = register_and_login(client)
    orphaned_token = create_access_token(subject=user["id"] + 1000)

    assert_unauthorized(client.get(ME_URL, headers=auth_header(orphaned_token)))


def test_me_never_exposes_password_material(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client)

    response = client.get(ME_URL, headers=auth_header(token))

    assert response.status_code == 200
    assert "password_hash" not in response.text
    assert "password" not in response.text
    assert RAW_PASSWORD not in response.text
