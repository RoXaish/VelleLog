import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

RAW_PASSWORD = "s3cure-passphrase"


def test_create_user(db_session: Session) -> None:
    """A user can be persisted with generated timestamps and an id."""
    user = User(
        email="alex@example.com",
        password_hash=hash_password(RAW_PASSWORD),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "alex@example.com"
    assert user.created_at is not None
    assert user.updated_at is not None


def test_email_must_be_unique(db_session: Session) -> None:
    """The database enforces a unique email address."""
    db_session.add(
        User(email="sam@example.com", password_hash=hash_password(RAW_PASSWORD))
    )
    db_session.commit()

    db_session.add(
        User(email="sam@example.com", password_hash=hash_password(RAW_PASSWORD))
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_password_is_hashed_and_not_stored_in_plaintext(db_session: Session) -> None:
    """Only the Argon2 hash is stored and it verifies against the raw password."""
    user = User(
        email="jordan@example.com",
        password_hash=hash_password(RAW_PASSWORD),
    )

    db_session.add(user)
    db_session.commit()

    stored_hash = db_session.execute(
        select(User.password_hash).where(User.email == "jordan@example.com")
    ).scalar_one()

    assert stored_hash != RAW_PASSWORD
    assert RAW_PASSWORD not in stored_hash
    assert stored_hash.startswith("$argon2")

    assert verify_password(RAW_PASSWORD, stored_hash) is True
    assert verify_password("incorrect-password", stored_hash) is False


def test_user_response_does_not_expose_password_hash(db_session: Session) -> None:
    """UserResponse serializes only public account fields."""
    assert "password_hash" not in UserResponse.model_fields

    user = User(
        email="taylor@example.com",
        password_hash=hash_password(RAW_PASSWORD),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    payload = UserResponse.model_validate(user).model_dump()

    assert "password_hash" not in payload
    assert "password" not in payload
    assert payload["email"] == "taylor@example.com"


def test_user_create_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password=RAW_PASSWORD)


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="alex@example.com", password="short")


def test_user_create_accepts_valid_email_and_password() -> None:
    user_create = UserCreate(email="alex@example.com", password=RAW_PASSWORD)

    assert user_create.email == "alex@example.com"
    assert user_create.password == RAW_PASSWORD
