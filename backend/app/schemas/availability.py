from datetime import time
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field


class MemberAvailabilityNow(BaseModel):
    """Current availability status of a group member (free or busy)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: EmailStr
    status: str  # "free" or "busy"


class AvailabilitySlotResponse(BaseModel):
    """A matching common free-time window for group members."""

    model_config = ConfigDict(from_attributes=True)

    start_time: time
    end_time: time
    duration_minutes: int
    free_members_count: int
    free_member_ids: list[int]

    @computed_field
    @property
    def free_member_count(self) -> int:
        return self.free_members_count
