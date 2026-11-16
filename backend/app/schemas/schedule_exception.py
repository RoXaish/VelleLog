from datetime import date as dt_date, datetime as dt_datetime, time as dt_time
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ScheduleExceptionCreate(BaseModel):
    """Payload to create a one-off schedule exception on a specific date."""

    date: dt_date
    start_time: dt_time
    end_time: dt_time
    exception_type: Literal["busy", "free"]
    private_label: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleExceptionCreate":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be strictly earlier than end_time")
        if self.private_label is not None:
            stripped = self.private_label.strip()
            self.private_label = stripped if stripped else None
        return self


class ScheduleExceptionUpdate(BaseModel):
    """Payload to update an existing schedule exception."""

    date: dt_date | None = None
    start_time: dt_time | None = None
    end_time: dt_time | None = None
    exception_type: Literal["busy", "free"] | None = None
    private_label: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleExceptionUpdate":
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


class ScheduleExceptionResponse(BaseModel):
    """Public representation of a user's schedule exception."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: dt_date
    start_time: dt_time
    end_time: dt_time
    exception_type: str
    private_label: str | None
    created_at: dt_datetime
    updated_at: dt_datetime
