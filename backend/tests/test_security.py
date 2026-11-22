import pytest

from app.core.security import hash_password, verify_password, verify_password_or_dummy

RAW_PASSWORD = "correct horse battery staple"


def test_hash_password_produces_argon2_hash() -> None:
    """
    Hashing must produce an Argon2 hash and never return the plaintext password.
    """
    password_hash = hash_password(RAW_PASSWORD)

    assert password_hash != RAW_PASSWORD
    assert password_hash.startswith("$argon2")
    assert RAW_PASSWORD not in password_hash


def test_verify_password_accepts_correct_password() -> None:
    password_hash = hash_password(RAW_PASSWORD)

    assert verify_password(RAW_PASSWORD, password_hash) is True


def test_verify_password_rejects_incorrect_password() -> None:
    password_hash = hash_password(RAW_PASSWORD)

    assert verify_password("wrong password", password_hash) is False


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "",
        "plaintext-password",
        "$argon2id$v=19$m=65536,t=3,p=4$not-valid-base64",
        "$2b$12$not-an-argon2-hash",
    ],
)
def test_verify_password_returns_false_for_invalid_hash(invalid_hash: str) -> None:
    """
    Malformed or foreign password hashes must fail verification safely
    instead of raising an exception.
    """
    assert verify_password(RAW_PASSWORD, invalid_hash) is False


def test_verify_password_or_dummy_rejects_unknown_account() -> None:
    """
    A missing stored hash still performs a failed verification rather than
    short-circuiting, which keeps unknown-email login timing closer to a
    wrong-password attempt.
    """
    assert verify_password_or_dummy(RAW_PASSWORD, None) is False


def test_verify_password_or_dummy_uses_real_hash_when_present() -> None:
    password_hash = hash_password(RAW_PASSWORD)

    assert verify_password_or_dummy(RAW_PASSWORD, password_hash) is True
    assert verify_password_or_dummy("wrong password", password_hash) is False
