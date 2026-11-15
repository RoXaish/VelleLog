from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field


def _normalize_email(value: Any) -> Any:
    """Trim surrounding whitespace and lowercase an email before validation."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]


class UserCreate(BaseModel):
    """Validated input for creating a user account."""

    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Validated input for authenticating an existing account."""

    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public user representation. Password material is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime
