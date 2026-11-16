from datetime import datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class BusyBlockCreate(BaseModel):
    """Payload to create a new weekly recurring busy block."""

    weekday: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time
    private_label: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_time_range(self) -> "BusyBlockCreate":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be strictly earlier than end_time")
        if self.private_label is not None:
            stripped = self.private_label.strip()
            self.private_label = stripped if stripped else None
        return self


class BusyBlockUpdate(BaseModel):
    """Payload to update an existing weekly recurring busy block."""

    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    private_label: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_time_range(self) -> "BusyBlockUpdate":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError("start_time must be strictly earlier than end_time")
        if self.private_label is not None:
            stripped = self.private_label.strip()
            self.private_label = stripped if stripped else None
        return self


class BusyBlockCopyDay(BaseModel):
    """Payload to copy all busy blocks from one weekday to another."""

    source_weekday: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    target_weekday: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")

    @model_validator(mode="after")
    def validate_different_days(self) -> "BusyBlockCopyDay":
        if self.source_weekday == self.target_weekday:
            raise ValueError("source_weekday and target_weekday must be different")
        return self


class BusyBlockResponse(BaseModel):
    """Public representation of a user's recurring busy block."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    weekday: int
    start_time: time
    end_time: time
    private_label: str | None
    created_at: datetime
    updated_at: datetime
