from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntry
    from app.models.user import User


journal_entry_tags = Table(
    "journal_entry_tags",
    Base.metadata,
    Column(
        "journal_entry_id",
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("ix_journal_entry_tags_tag_id", "tag_id"),
)


class Tag(Base):
    """A user-owned label that can be attached to journal entries."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
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
        back_populates="tags",
        foreign_keys=[user_id],
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        "JournalEntry",
        secondary=journal_entry_tags,
        back_populates="tags",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0 AND length(name) <= 50",
            name="ck_tags_name_length",
        ),
        UniqueConstraint("user_id", "name", name="uq_tags_user_id_name"),
        Index("ix_tags_user_id_name", "user_id", "name"),
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("tag name must not be empty")
            if len(stripped) > 50:
                raise ValueError("tag name must be 50 characters or fewer")
            return stripped
        return value
