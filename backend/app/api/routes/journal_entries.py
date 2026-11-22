from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CsrfProtectedUser, CurrentUser
from app.core.moods import Mood
from app.db.session import get_db
from app.models.journal_entry import JournalEntry
from app.models.tag import Tag, journal_entry_tags
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryListResponse,
    JournalEntryResponse,
    JournalEntryUpdate,
)

router = APIRouter(prefix="/journal-entries", tags=["journal"])

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _get_owned_entry(db: Session, entry_id: int, user_id: int) -> JournalEntry:
    entry = db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.tags))
        .where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == user_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )
    return entry


def _resolve_tags(
    db: Session,
    tag_ids: list[int],
    user_id: int,
) -> list[Tag]:
    """Resolve owned tags, rejecting ids that do not belong to the user."""
    unique_ids = list(dict.fromkeys(tag_ids))
    if not unique_ids:
        return []

    tags = (
        db.execute(
            select(Tag).where(
                Tag.id.in_(unique_ids),
                Tag.user_id == user_id,
            )
        )
        .scalars()
        .all()
    )

    if len(tags) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return tags


@router.post(
    "",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a private journal entry",
)
def create_journal_entry(
    payload: JournalEntryCreate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    """Create a new journal entry owned by the authenticated user."""
    entry = JournalEntry(
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        mood=payload.mood.value if payload.mood is not None else None,
        tags=_resolve_tags(db, payload.tag_ids, current_user.id),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return JournalEntryResponse.model_validate(entry)


@router.get(
    "",
    response_model=JournalEntryListResponse,
    summary="List the authenticated user's journal entries",
)
def list_journal_entries(
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(default=None, max_length=200),
    tag_ids: list[int] | None = Query(default=None),
    mood: Mood | None = Query(default=None),
    db: Session = Depends(get_db),
) -> JournalEntryListResponse:
    """
    Return the authenticated user's journal entries newest first.

    Supports optional case-insensitive search across titles and content,
    mood filtering, AND-style tag filtering, and offset pagination. Entries
    belonging to other users are never included.
    """
    filters = [JournalEntry.user_id == current_user.id]

    if search is not None and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        filters.append(
            or_(
                JournalEntry.title.ilike(pattern, escape="\\"),
                JournalEntry.content.ilike(pattern, escape="\\"),
            )
        )

    if tag_ids:
        unique_tag_ids = list(dict.fromkeys(tag_ids))
        owned_tag_ids = set(
            db.execute(
                select(Tag.id).where(
                    Tag.id.in_(unique_tag_ids),
                    Tag.user_id == current_user.id,
                )
            )
            .scalars()
            .all()
        )
        if len(owned_tag_ids) != len(unique_tag_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )

        tagged_entry_ids = (
            select(journal_entry_tags.c.journal_entry_id)
            .where(journal_entry_tags.c.tag_id.in_(unique_tag_ids))
            .group_by(journal_entry_tags.c.journal_entry_id)
            .having(
                func.count(func.distinct(journal_entry_tags.c.tag_id))
                == len(unique_tag_ids)
            )
        )
        filters.append(JournalEntry.id.in_(tagged_entry_ids))

    if mood is not None:
        filters.append(JournalEntry.mood == mood.value)

    total = db.execute(
        select(func.count()).select_from(JournalEntry).where(*filters)
    ).scalar_one()

    entries = (
        db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.tags))
            .where(*filters)
            .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    total_pages = (total + page_size - 1) // page_size if total else 0
    return JournalEntryListResponse(
        items=[JournalEntryResponse.model_validate(entry) for entry in entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1 and total_pages > 0,
    )


@router.get(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Get a single journal entry",
)
def get_journal_entry(
    entry_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    """Return one entry only when it belongs to the authenticated user."""
    entry = _get_owned_entry(db, entry_id, current_user.id)
    return JournalEntryResponse.model_validate(entry)


@router.patch(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Update a journal entry",
)
def update_journal_entry(
    entry_id: int,
    payload: JournalEntryUpdate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    """Update the title and/or content of an entry owned by the current user."""
    entry = _get_owned_entry(db, entry_id, current_user.id)

    if payload.title is not None:
        entry.title = payload.title
    if payload.content is not None:
        entry.content = payload.content
    if "mood" in payload.model_fields_set:
        entry.mood = payload.mood.value if payload.mood is not None else None
    if payload.tag_ids is not None:
        entry.tags = _resolve_tags(db, payload.tag_ids, current_user.id)

    db.commit()
    db.refresh(entry)
    return JournalEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a journal entry",
)
def delete_journal_entry(
    entry_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> Response:
    """Permanently delete an entry owned by the authenticated user."""
    entry = _get_owned_entry(db, entry_id, current_user.id)
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
