from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.journal_entry import JournalEntry
from app.schemas.dashboard import DashboardResponse
from app.schemas.journal_entry import JournalEntryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_ENTRY_LIMIT = 5


def _coerce_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _current_streak(db: Session, user_id: int, today: date) -> int:
    """Count consecutive writing days ending today or yesterday."""
    written_dates = [
        _coerce_date(value)
        for value in db.execute(
            select(func.date(JournalEntry.created_at))
            .where(JournalEntry.user_id == user_id)
            .group_by(func.date(JournalEntry.created_at))
            .order_by(func.date(JournalEntry.created_at).desc())
        )
        .scalars()
        .all()
    ]

    if not written_dates:
        return 0

    yesterday = today - timedelta(days=1)
    if written_dates[0] == today:
        expected = today
    elif written_dates[0] == yesterday:
        expected = yesterday
    else:
        return 0

    streak = 0
    for written_date in written_dates:
        if written_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif written_date < expected:
            break

    return streak


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get the authenticated user's writing dashboard",
)
def get_dashboard(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Return counts, streak, and recent entries for the current user."""
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start_date = today - timedelta(days=today.weekday())
    week_start = datetime.combine(
        week_start_date,
        time.min,
        tzinfo=timezone.utc,
    )

    total_entries = db.execute(
        select(func.count())
        .select_from(JournalEntry)
        .where(JournalEntry.user_id == current_user.id)
    ).scalar_one()

    entries_this_week = db.execute(
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.user_id == current_user.id,
            JournalEntry.created_at >= week_start,
        )
    ).scalar_one()

    recent_entries = (
        db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.tags))
            .where(JournalEntry.user_id == current_user.id)
            .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
            .limit(RECENT_ENTRY_LIMIT)
        )
        .scalars()
        .all()
    )

    return DashboardResponse(
        total_entries=total_entries,
        entries_this_week=entries_this_week,
        current_streak=_current_streak(db, current_user.id, today),
        recent_entries=[
            JournalEntryResponse.model_validate(entry)
            for entry in recent_entries
        ],
    )
