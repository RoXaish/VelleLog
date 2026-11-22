from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.moods import MOOD_SQL_LIST, Mood
from app.db.base import Base
from app.models.tag import Tag, journal_entry_tags

if TYPE_CHECKING:
    from app.models.user import User


class JournalEntry(Base):
    """A private journal entry owned by a single user."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    mood: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="journal_entries",
        foreign_keys=[user_id],
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary=journal_entry_tags,
        back_populates="journal_entries",
        lazy="selectin",
        order_by="Tag.name",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0 AND length(title) <= 200",
            name="ck_journal_entries_title_length",
        ),
        CheckConstraint(
            "length(trim(content)) > 0 AND length(content) <= 50000",
            name="ck_journal_entries_content_length",
        ),
        CheckConstraint(
            f"mood IS NULL OR mood IN ({MOOD_SQL_LIST})",
            name="ck_journal_entries_mood",
        ),
        Index("ix_journal_entries_user_id_created_at", "user_id", "created_at"),
        Index("ix_journal_entries_user_id_mood", "user_id", "mood"),
    )

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("title must not be empty")
            if len(stripped) > 200:
                raise ValueError("title must be 200 characters or fewer")
            return stripped
        return value

    @validates("content")
    def validate_content(self, key: str, value: str) -> str:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("content must not be empty")
            if len(stripped) > 50000:
                raise ValueError("content must be 50000 characters or fewer")
            return stripped
        return value

    @validates("mood")
    def validate_mood(self, key: str, value: str | Mood | None) -> str | None:
        if value is None:
            return None
        try:
            return Mood(value).value
        except ValueError as exc:
            raise ValueError("unsupported mood") from exc
