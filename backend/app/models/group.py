from datetime import datetime
import enum
import secrets
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class GroupRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


def generate_invite_code(length: int = 12) -> str:
    """Generate a cryptographically secure, URL-safe invite code."""
    return secrets.token_urlsafe(length)[:length]


class Group(Base):
    """A friend group circle in Velle Log."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=generate_invite_code,
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_groups",
        foreign_keys=[owner_id],
    )
    memberships: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="GroupMembership.joined_at",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure creator automatically has an owner membership in memory upon instantiation
        owner_id = self.owner_id
        owner = getattr(self, "owner", None) or kwargs.get("owner")
        if owner_id is not None:
            if not any(m.user_id == owner_id for m in self.memberships):
                self.memberships.append(
                    GroupMembership(user_id=owner_id, role=GroupRole.OWNER.value)
                )
        elif owner is not None:
            if not any(m.user == owner for m in self.memberships):
                self.memberships.append(
                    GroupMembership(user=owner, role=GroupRole.OWNER.value)
                )


class GroupMembership(Base):
    """Membership mapping associating users to groups with a designated role."""

    __tablename__ = "group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=GroupRole.MEMBER.value,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    group: Mapped["Group"] = relationship(
        "Group",
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="group_memberships",
    )

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "user_id",
            name="uq_group_memberships_group_id_user_id",
        ),
        CheckConstraint(
            "role IN ('owner', 'member')",
            name="ck_group_memberships_role",
        ),
        Index("ix_group_memberships_role", "role"),
    )


@event.listens_for(Session, "before_flush")
def _auto_create_group_owner_membership(
    session: Session, flush_context, instances
) -> None:
    """
    Ensure that whenever a new Group is flushed to the database,
    an owner membership for the creator is guaranteed to exist.
    """
    for obj in session.new:
        if isinstance(obj, Group):
            owner_id = obj.owner_id
            owner = obj.owner
            if owner_id is not None or owner is not None:
                has_owner = any(
                    m.role == GroupRole.OWNER.value
                    and (
                        (owner_id is not None and m.user_id == owner_id)
                        or (
                            owner is not None
                            and (m.user == owner or m.user_id == getattr(owner, "id", None))
                        )
                    )
                    for m in obj.memberships
                )
                if not has_owner:
                    membership = GroupMembership(
                        group=obj,
                        user_id=owner_id,
                        user=owner if owner_id is None else None,
                        role=GroupRole.OWNER.value,
                    )
                    obj.memberships.append(membership)
