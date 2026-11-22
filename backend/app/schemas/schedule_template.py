from datetime import datetime as dt_datetime, time as dt_time
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class TemplateBusyBlockCreate(BaseModel):
    """Payload to create a busy block inside a schedule template."""

    weekday: int = Field(..., ge=0, le=6, description="Weekday index: 0=Monday, 6=Sunday")
    start_time: dt_time
    end_time: dt_time

    @model_validator(mode="after")
    def validate_time_range(self) -> "TemplateBusyBlockCreate":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be strictly earlier than end_time")
        return self


class TemplateBusyBlockUpdate(BaseModel):
    """Payload to update an existing template busy block."""

    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: dt_time | None = None
    end_time: dt_time | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "TemplateBusyBlockUpdate":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError("start_time must be strictly earlier than end_time")
        return self


class TemplateBusyBlockResponse(BaseModel):
    """Public representation of a template busy block."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    weekday: int
    start_time: dt_time
    end_time: dt_time
    created_at: dt_datetime
    updated_at: dt_datetime


class ScheduleTemplateCreate(BaseModel):
    """Payload to create a shared schedule template for a group circle."""

    name: str = Field(..., min_length=1, max_length=100)
    blocks: list[TemplateBusyBlockCreate] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty or whitespace only")
        return stripped


class ScheduleTemplateUpdate(BaseModel):
    """Payload to rename an existing schedule template."""

    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty or whitespace only")
        return stripped


class ScheduleTemplateResponse(BaseModel):
    """Public representation of a schedule template with its blocks."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str
    created_by_user_id: int | None = None
    is_applied: bool = False
    blocks: list[TemplateBusyBlockResponse] = Field(default_factory=list)
    created_at: dt_datetime
    updated_at: dt_datetime


class AppliedTemplateResponse(BaseModel):
    """Response representing an applied template on a user's recurring schedule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    template_id: int
    applied_at: dt_datetime
