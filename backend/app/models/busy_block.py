from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class BusyBlock(Base):
    """
    A recurring weekly busy time block for an individual user.

    Weekday mapping: 0 = Monday, 1 = Tuesday, ..., 6 = Sunday.
    Time range: start_time must be strictly earlier than end_time.
    """

    __tablename__ = "busy_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    private_label: Mapped[str | None] = mapped_column(
        String(255),
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
        back_populates="busy_blocks",
        foreign_keys=[user_id],
    )

    __table_args__ = (
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_busy_blocks_weekday",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_busy_blocks_time_range",
        ),
        Index("ix_busy_blocks_user_id_weekday", "user_id", "weekday"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.weekday is not None and not (0 <= self.weekday <= 6):
            raise ValueError(f"weekday must be between 0 and 6, got {self.weekday}")
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError(
                f"start_time ({self.start_time}) must be strictly earlier than end_time ({self.end_time})"
            )

    @validates("weekday")
    def validate_weekday(self, key: str, value: int) -> int:
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool) or not (0 <= value <= 6):
                raise ValueError(
                    f"weekday must be an integer between 0 (Monday) and 6 (Sunday), got {value!r}"
                )
        return value

    @validates("start_time")
    def validate_start_time(self, key: str, value: time) -> time:
        if value is not None and getattr(self, "end_time", None) is not None:
            if value >= self.end_time:
                raise ValueError(
                    f"start_time ({value}) must be strictly earlier than end_time ({self.end_time})"
                )
        return value

    @validates("end_time")
    def validate_end_time(self, key: str, value: time) -> time:
        if value is not None and getattr(self, "start_time", None) is not None:
            if getattr(self, "start_time", None) >= value:
                raise ValueError(
                    f"end_time ({value}) must be strictly later than start_time ({self.start_time})"
                )
        return value
