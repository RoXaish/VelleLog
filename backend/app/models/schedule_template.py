from datetime import datetime, time as dt_time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.user import User


class ScheduleTemplate(Base):
    """
    A shared weekly timetable template belonging to a group circle.
    Contains template busy blocks that members can apply to their recurring schedules.
    """

    __tablename__ = "schedule_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
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

    # Relationships
    group: Mapped["Group"] = relationship(
        "Group",
        back_populates="templates",
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
    blocks: Mapped[list["TemplateBusyBlock"]] = relationship(
        "TemplateBusyBlock",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateBusyBlock.weekday, TemplateBusyBlock.start_time",
    )
    applications: Mapped[list["AppliedScheduleTemplate"]] = relationship(
        "AppliedScheduleTemplate",
        back_populates="template",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_schedule_templates_name_not_empty",
        ),
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Template name must not be empty or whitespace only")
        return value.strip()


class TemplateBusyBlock(Base):
    """
    A recurring weekly busy block belonging to a shared ScheduleTemplate.
    Weekday mapping: 0 = Monday, ..., 6 = Sunday.
    """

    __tablename__ = "template_busy_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_templates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_time: Mapped[dt_time] = mapped_column(
        Time,
        nullable=False,
    )
    end_time: Mapped[dt_time] = mapped_column(
        Time,
        nullable=False,
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

    template: Mapped["ScheduleTemplate"] = relationship(
        "ScheduleTemplate",
        back_populates="blocks",
    )

    __table_args__ = (
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_template_busy_blocks_weekday",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_template_busy_blocks_time_range",
        ),
        Index(
            "ix_template_busy_blocks_template_id_weekday",
            "template_id",
            "weekday",
        ),
    )

    @validates("weekday")
    def validate_weekday(self, key: str, value: int) -> int:
        if not (0 <= value <= 6):
            raise ValueError(f"weekday must be between 0 (Monday) and 6 (Sunday), got {value}")
        return value

    @validates("end_time")
    def validate_end_time(self, key: str, value: dt_time) -> dt_time:
        if self.start_time is not None and value <= self.start_time:
            raise ValueError(
                f"end_time ({value}) must be strictly later than start_time ({self.start_time})"
            )
        return value


class AppliedScheduleTemplate(Base):
    """
    Tracking association linking an individual user to a shared ScheduleTemplate
    they have applied to their recurring schedule.
    Enforces uniqueness so a template cannot be applied multiple times by the same user.
    """

    __tablename__ = "applied_schedule_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_templates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="applied_templates",
    )
    template: Mapped["ScheduleTemplate"] = relationship(
        "ScheduleTemplate",
        back_populates="applications",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "template_id",
            name="uq_user_applied_template",
        ),
    )
