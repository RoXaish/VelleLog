from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.tokens import decode_access_token

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
RAW_PASSWORD = "s3cure-passphrase"
GENERIC_LOGIN_ERROR = {"detail": "Invalid email or password"}


def register_user(
    client: TestClient,
    email: str = "alex@example.com",
    password: str = RAW_PASSWORD,
) -> dict:
    response = client.post(REGISTER_URL, json={"email": email, "password": password})
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str, password: str):
    return client.post(LOGIN_URL, json={"email": email, "password": password})


def test_login_success(client: TestClient, db_session: Session) -> None:
    register_user(client)

    response = login(client, "alex@example.com", RAW_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_login_token_contains_user_subject_and_expiration(
    client: TestClient, db_session: Session
) -> None:
    user = register_user(client)

    response = login(client, "alex@example.com", RAW_PASSWORD)
    payload = decode_access_token(response.json()["access_token"])

    assert payload["sub"] == str(user["id"])
    assert isinstance(payload["exp"], int)
    assert datetime.fromtimestamp(payload["exp"], tz=timezone.utc) > datetime.now(
        timezone.utc
    )


def test_login_normalizes_email(client: TestClient, db_session: Session) -> None:
    register_user(client, email="Jordan@Example.com")

    response = login(client, "  JORDAN@EXAMPLE.COM  ", RAW_PASSWORD)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_incorrect_password_returns_generic_401(
    client: TestClient, db_session: Session
) -> None:
    register_user(client)

    response = login(client, "alex@example.com", "incorrect-password")

    assert response.status_code == 401
    assert response.json() == GENERIC_LOGIN_ERROR
    assert "access_token" not in response.json()


def test_login_unknown_email_returns_same_generic_401(
    client: TestClient, db_session: Session
) -> None:
    register_user(client)

    unknown_email_response = login(client, "unknown@example.com", RAW_PASSWORD)
    wrong_password_response = login(client, "alex@example.com", "incorrect-password")

    assert unknown_email_response.status_code == 401
    assert unknown_email_response.json() == GENERIC_LOGIN_ERROR
    assert unknown_email_response.status_code == wrong_password_response.status_code
    assert unknown_email_response.json() == wrong_password_response.json()


def test_login_response_never_exposes_password_material(
    client: TestClient, db_session: Session
) -> None:
    register_user(client)

    response = login(client, "alex@example.com", RAW_PASSWORD)

    assert RAW_PASSWORD not in response.text
    assert "password_hash" not in response.text
    assert "password" not in response.text


def test_login_validation_error_does_not_echo_password(
    client: TestClient, db_session: Session
) -> None:
    submitted_password = "x" * 129

    response = login(client, "alex@example.com", submitted_password)

    assert response.status_code == 422
    assert submitted_password not in response.text
