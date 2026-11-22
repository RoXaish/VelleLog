"""Pydantic schemas package for request and response validation."""

from app.schemas.availability import (
    AvailabilitySlotResponse,
    MemberAvailabilityNow,
)
from app.schemas.busy_block import (
    BusyBlockCopyDay,
    BusyBlockCreate,
    BusyBlockResponse,
    BusyBlockUpdate,
)
from app.schemas.dashboard import DashboardResponse
from app.schemas.group import (
    GroupCreate,
    GroupDetailResponse,
    GroupJoin,
    GroupMemberResponse,
    GroupResponse,
)
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryListResponse,
    JournalEntryResponse,
    JournalEntryUpdate,
)
from app.schemas.schedule_exception import (
    ScheduleExceptionCreate,
    ScheduleExceptionResponse,
    ScheduleExceptionUpdate,
)
from app.schemas.schedule_template import (
    AppliedTemplateResponse,
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    ScheduleTemplateUpdate,
    TemplateBusyBlockCreate,
    TemplateBusyBlockResponse,
    TemplateBusyBlockUpdate,
)
from app.schemas.tag import TagCreate, TagResponse, TagSummary, TagUpdate
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse

__all__ = [
    "AppliedTemplateResponse",
    "AvailabilitySlotResponse",
    "BusyBlockCopyDay",
    "BusyBlockCreate",
    "BusyBlockResponse",
    "BusyBlockUpdate",
    "DashboardResponse",
    "GroupCreate",
    "GroupDetailResponse",
    "GroupJoin",
    "GroupMemberResponse",
    "GroupResponse",
    "JournalEntryCreate",
    "JournalEntryListResponse",
    "JournalEntryResponse",
    "JournalEntryUpdate",
    "MemberAvailabilityNow",
    "ScheduleExceptionCreate",
    "ScheduleExceptionResponse",
    "ScheduleExceptionUpdate",
    "ScheduleTemplateCreate",
    "ScheduleTemplateResponse",
    "ScheduleTemplateUpdate",
    "TagCreate",
    "TagResponse",
    "TagSummary",
    "TagUpdate",
    "TemplateBusyBlockCreate",
    "TemplateBusyBlockResponse",
    "TemplateBusyBlockUpdate",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
]
