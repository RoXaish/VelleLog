from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_password_hasher = PasswordHasher()
_DUMMY_PASSWORD_HASH = _password_hasher.hash("velle-log-dummy-password")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored Argon2 hash.

    Returns False for mismatches and malformed/unsupported hashes instead of
    raising, so corrupt data cannot break authentication flows.
    """
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    """
    Verify a password while always performing Argon2 work.

    When no stored hash is available (for example, an unknown email address),
    a dummy hash is verified instead so failed logins take comparable time and
    do not reveal whether an account exists.
    """
    return verify_password(password, password_hash or _DUMMY_PASSWORD_HASH)
