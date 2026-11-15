import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User

REGISTER_URL = "/api/auth/register"
RAW_PASSWORD = "s3cure-passphrase"
PUBLIC_FIELDS = {"id", "email", "created_at", "updated_at"}


def test_register_user_success(client: TestClient, db_session: Session) -> None:
    response = client.post(
        REGISTER_URL,
        json={"email": "alex@example.com", "password": RAW_PASSWORD},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "alex@example.com"


def test_register_returns_only_public_fields(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        REGISTER_URL,
        json={"email": "sam@example.com", "password": RAW_PASSWORD},
    )

    assert response.status_code == 201
    body = response.json()

    assert set(body) == PUBLIC_FIELDS
    assert isinstance(body["id"], int)
    assert body["created_at"]
    assert body["updated_at"]
    assert "password" not in body
    assert "password_hash" not in body
    assert RAW_PASSWORD not in response.text


def test_register_stores_password_hash_not_plaintext(
    client: TestClient, db_session: Session
) -> None:
    client.post(
        REGISTER_URL,
        json={"email": "jordan@example.com", "password": RAW_PASSWORD},
    )

    user = db_session.execute(
        select(User).where(User.email == "jordan@example.com")
    ).scalar_one()

    assert user.password_hash != RAW_PASSWORD
    assert RAW_PASSWORD not in user.password_hash
    assert user.password_hash.startswith("$argon2")
    assert verify_password(RAW_PASSWORD, user.password_hash) is True


def test_register_duplicate_email_returns_409(
    client: TestClient, db_session: Session
) -> None:
    payload = {"email": "taylor@example.com", "password": RAW_PASSWORD}

    first = client.post(REGISTER_URL, json=payload)
    second = client.post(REGISTER_URL, json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"
    assert "UNIQUE constraint" not in second.text


def test_register_normalizes_email(client: TestClient, db_session: Session) -> None:
    response = client.post(
        REGISTER_URL,
        json={"email": "  Alex@Example.COM  ", "password": RAW_PASSWORD},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "alex@example.com"

    user = db_session.execute(
        select(User).where(User.email == "alex@example.com")
    ).scalar_one()
    assert user.email == "alex@example.com"

    duplicate = client.post(
        REGISTER_URL,
        json={"email": "ALEX@example.com", "password": RAW_PASSWORD},
    )
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "alex@",
        "@example.com",
        "alex example@example.com",
    ],
)
def test_register_invalid_email_returns_422(
    client: TestClient, db_session: Session, email: str
) -> None:
    response = client.post(
        REGISTER_URL,
        json={"email": email, "password": RAW_PASSWORD},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "alex@example.com", "password": "short"},
        {"email": "alex@example.com"},
        {"email": "alex@example.com", "password": "x" * 129},
    ],
)
def test_register_invalid_password_returns_422(
    client: TestClient, db_session: Session, payload: dict[str, str]
) -> None:
    response = client.post(REGISTER_URL, json=payload)

    assert response.status_code == 422


def test_register_validation_error_does_not_echo_password(
    client: TestClient, db_session: Session
) -> None:
    submitted_password = "shortpw"

    response = client.post(
        REGISTER_URL,
        json={"email": "alex@example.com", "password": submitted_password},
    )

    assert response.status_code == 422
    assert submitted_password not in response.text


def test_health_endpoint_still_works(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
