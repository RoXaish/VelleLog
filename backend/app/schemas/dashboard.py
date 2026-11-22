from pydantic import BaseModel

from app.schemas.journal_entry import JournalEntryResponse


class DashboardResponse(BaseModel):
    """Personalized writing overview for the authenticated user."""

    total_entries: int
    entries_this_week: int
    current_streak: int
    recent_entries: list[JournalEntryResponse]
