from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.group import Group, GroupMembership


class User(Base):
    """Application user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
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

    owned_groups: Mapped[list["Group"]] = relationship(
        "Group",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="Group.owner_id",
    )
    group_memberships: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="GroupMembership.user_id",
    )
