from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.moods import Mood
from app.schemas.tag import TagSummary

MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 50000
MAX_TAGS_PER_ENTRY = 20


class JournalEntryCreate(BaseModel):
    """Payload to create a private journal entry."""

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)
    mood: Mood | None = None
    tag_ids: list[int] = Field(
        default_factory=list,
        max_length=MAX_TAGS_PER_ENTRY,
    )

    @field_validator("tag_ids")
    @classmethod
    def deduplicate_tag_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must not be empty")
        return stripped


class JournalEntryUpdate(BaseModel):
    """Payload to update a journal entry. At least one field is required."""

    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE_LENGTH)
    content: str | None = Field(
        default=None, min_length=1, max_length=MAX_CONTENT_LENGTH
    )
    mood: Mood | None = None
    tag_ids: list[int] | None = Field(
        default=None,
        max_length=MAX_TAGS_PER_ENTRY,
    )

    @field_validator("tag_ids")
    @classmethod
    def deduplicate_tag_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        return list(dict.fromkeys(value))

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must not be empty")
        return stripped

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "JournalEntryUpdate":
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        for field_name in ("title", "content", "tag_ids"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class JournalEntryResponse(BaseModel):
    """Public representation of a journal entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    content: str
    mood: Mood | None = None
    tags: list[TagSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class JournalEntryListResponse(BaseModel):
    """Paginated journal entries ordered newest first."""

    items: list[JournalEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
