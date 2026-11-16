from datetime import datetime
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.group import Group, GroupMembership, GroupRole, generate_invite_code
from app.models.user import User


def _create_test_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash=hash_password("s3cure-passphrase"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_group_generates_id_timestamp_and_invite_code(db_session: Session) -> None:
    """A group can be persisted with name, unique invite_code, and owner_id."""
    owner = _create_test_user(db_session, "owner@example.com")

    group = Group(name="Weekend Crew", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    assert group.id is not None
    assert group.name == "Weekend Crew"
    assert group.owner_id == owner.id
    assert group.invite_code is not None
    assert len(group.invite_code) >= 8
    assert isinstance(group.created_at, datetime)


def test_create_group_accepts_custom_invite_code(db_session: Session) -> None:
    """A custom invite code can be provided upon group creation."""
    owner = _create_test_user(db_session, "custom_code_owner@example.com")

    custom_code = "SECRET123"
    group = Group(name="Private Circle", owner_id=owner.id, invite_code=custom_code)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    assert group.invite_code == custom_code


def test_group_creator_automatically_becomes_owner_member(db_session: Session) -> None:
    """When a group is created, the creator automatically becomes a member with the 'owner' role."""
    owner = _create_test_user(db_session, "creator@example.com")

    group = Group(name="Board Game Club", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    # Creator must automatically have a membership with role 'owner'
    assert len(group.memberships) == 1
    membership = group.memberships[0]
    assert membership.user_id == owner.id
    assert membership.group_id == group.id
    assert membership.role == GroupRole.OWNER.value
    assert isinstance(membership.joined_at, datetime)


def test_group_creator_via_relationship_automatically_becomes_owner_member(db_session: Session) -> None:
    """Assigning group.owner via object relationship also establishes owner membership."""
    owner = _create_test_user(db_session, "rel_owner@example.com")

    group = Group(name="Hiking Friends", owner=owner)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    assert len(group.memberships) == 1
    assert group.memberships[0].user_id == owner.id
    assert group.memberships[0].role == GroupRole.OWNER.value


def test_add_group_member(db_session: Session) -> None:
    """Additional members can join a group with the 'member' role."""
    owner = _create_test_user(db_session, "group_owner@example.com")
    member = _create_test_user(db_session, "group_member@example.com")

    group = Group(name="Study Group", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()

    # Add second user as member
    membership = GroupMembership(
        group_id=group.id,
        user_id=member.id,
        role=GroupRole.MEMBER.value,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(group)

    assert len(group.memberships) == 2
    roles = {m.user_id: m.role for m in group.memberships}
    assert roles[owner.id] == GroupRole.OWNER.value
    assert roles[member.id] == GroupRole.MEMBER.value


def test_unique_group_user_membership_enforced(db_session: Session) -> None:
    """A user cannot have duplicate memberships in the same group."""
    owner = _create_test_user(db_session, "dup_owner@example.com")
    member = _create_test_user(db_session, "dup_member@example.com")

    group = Group(name="Tennis Group", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()

    # First membership for member succeeds
    db_session.add(
        GroupMembership(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER.value)
    )
    db_session.commit()

    # Second duplicate membership must raise IntegrityError
    db_session.add(
        GroupMembership(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER.value)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_unique_group_invite_code_enforced(db_session: Session) -> None:
    """Duplicate invite codes across groups are rejected by the database."""
    owner1 = _create_test_user(db_session, "invite1@example.com")
    owner2 = _create_test_user(db_session, "invite2@example.com")

    shared_code = "NON_UNIQUE_CODE"
    db_session.add(Group(name="Group One", owner_id=owner1.id, invite_code=shared_code))
    db_session.commit()

    db_session.add(Group(name="Group Two", owner_id=owner2.id, invite_code=shared_code))
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_foreign_key_invalid_owner_id_rejected(db_session: Session) -> None:
    """Creating a group with a non-existent owner_id violates foreign-key constraint."""
    non_existent_user_id = 999_999
    group = Group(name="Ghost Group", owner_id=non_existent_user_id)
    db_session.add(group)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_foreign_key_invalid_group_id_or_user_id_rejected(db_session: Session) -> None:
    """Adding a membership with a non-existent group_id or user_id violates foreign keys."""
    user = _create_test_user(db_session, "valid_user@example.com")
    non_existent_id = 999_999

    # Invalid group_id
    db_session.add(
        GroupMembership(
            group_id=non_existent_id,
            user_id=user.id,
            role=GroupRole.MEMBER.value,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_cascade_delete_group_removes_memberships(db_session: Session) -> None:
    """Deleting a group automatically removes all its memberships."""
    owner = _create_test_user(db_session, "cascade_owner@example.com")
    member = _create_test_user(db_session, "cascade_member@example.com")

    group = Group(name="Temporary Circle", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()

    db_session.add(
        GroupMembership(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER.value)
    )
    db_session.commit()

    group_id = group.id
    # Delete the group
    db_session.delete(group)
    db_session.commit()

    # Verify no orphan memberships remain
    remaining_memberships = db_session.execute(
        select(GroupMembership).where(GroupMembership.group_id == group_id)
    ).scalars().all()
    assert len(remaining_memberships) == 0


def test_cascade_delete_owner_removes_group(db_session: Session) -> None:
    """Deleting an owner user deletes their owned groups and associated memberships."""
    owner = _create_test_user(db_session, "deleted_owner@example.com")

    group = Group(name="Ownerless Group", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()
    group_id = group.id

    db_session.delete(owner)
    db_session.commit()

    # Group must be deleted
    found_group = db_session.execute(
        select(Group).where(Group.id == group_id)
    ).scalar_one_or_none()
    assert found_group is None

    # Memberships must be deleted
    remaining_memberships = db_session.execute(
        select(GroupMembership).where(GroupMembership.group_id == group_id)
    ).scalars().all()
    assert len(remaining_memberships) == 0


@pytest.mark.parametrize("invalid_role", ["admin", "guest", "OWNER", "MEMBER", "superadmin", ""])
def test_group_membership_invalid_role_rejected(
    db_session: Session, invalid_role: str
) -> None:
    """GroupMembership rejects any role not in ('owner', 'member') at the database level."""
    owner = _create_test_user(db_session, f"owner_{invalid_role or 'empty'}@example.com")
    member = _create_test_user(db_session, f"member_{invalid_role or 'empty'}@example.com")

    group = Group(name="Role Test Group", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()

    invalid_membership = GroupMembership(
        group_id=group.id,
        user_id=member.id,
        role=invalid_role,
    )
    db_session.add(invalid_membership)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_group_membership_valid_roles_accepted(db_session: Session) -> None:
    """GroupMembership accepts both valid roles ('owner' and 'member')."""
    owner = _create_test_user(db_session, "valid_roles_owner@example.com")
    member = _create_test_user(db_session, "valid_roles_member@example.com")

    group = Group(name="Valid Roles Group", owner_id=owner.id)
    db_session.add(group)
    db_session.commit()

    # Creator's membership role is 'owner'
    assert group.memberships[0].role == "owner"

    # Add second member with role 'member'
    membership = GroupMembership(
        group_id=group.id,
        user_id=member.id,
        role="member",
    )
    db_session.add(membership)
    db_session.commit()

    # Query back and verify both roles are persisted cleanly
    persisted = (
        db_session.execute(
            select(GroupMembership)
            .where(GroupMembership.group_id == group.id)
            .order_by(GroupMembership.id)
        )
        .scalars()
        .all()
    )
    assert len(persisted) == 2
    assert persisted[0].role == "owner"
    assert persisted[1].role == "member"

