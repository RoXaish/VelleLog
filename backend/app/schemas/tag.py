from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_TAG_NAME_LENGTH = 50


class TagCreate(BaseModel):
    """Payload to create a user-owned tag."""

    name: str = Field(min_length=1, max_length=MAX_TAG_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("tag name must not be empty")
        return stripped


class TagUpdate(BaseModel):
    """Payload to rename a user-owned tag."""

    name: str = Field(min_length=1, max_length=MAX_TAG_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("tag name must not be empty")
        return stripped


class TagSummary(BaseModel):
    """Compact tag representation embedded in journal entries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TagResponse(BaseModel):
    """Full tag representation including how many entries use it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime
