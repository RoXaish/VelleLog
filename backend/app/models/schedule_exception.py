from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ScheduleException(Base):
    """
    A one-off schedule exception for an individual user on a specific date.

    exception_type:
      - 'busy': adds a one-time busy interval.
      - 'free': overrides recurring busy blocks for that interval.
    """

    __tablename__ = "schedule_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        Date,
        index=True,
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
    exception_type: Mapped[str] = mapped_column(
        String(10),
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
        back_populates="schedule_exceptions",
        foreign_keys=[user_id],
    )

    __table_args__ = (
        CheckConstraint(
            "start_time < end_time",
            name="ck_schedule_exceptions_time_range",
        ),
        CheckConstraint(
            "exception_type IN ('busy', 'free')",
            name="ck_schedule_exceptions_type",
        ),
        Index("ix_schedule_exceptions_user_id_date", "user_id", "date"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.exception_type is not None and self.exception_type not in ("busy", "free"):
            raise ValueError(f"exception_type must be 'busy' or 'free', got {self.exception_type!r}")
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError(
                f"start_time ({self.start_time}) must be strictly earlier than end_time ({self.end_time})"
            )

    @validates("exception_type")
    def validate_exception_type(self, key: str, value: str) -> str:
        if value is not None and value not in ("busy", "free"):
            raise ValueError(f"exception_type must be 'busy' or 'free', got {value!r}")
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
