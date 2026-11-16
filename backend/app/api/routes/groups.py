from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.group import Group, GroupMembership, GroupRole
from app.schemas.group import (
    GroupCreate,
    GroupDetailResponse,
    GroupJoin,
    GroupResponse,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new group circle",
)
def create_group(
    payload: GroupCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> GroupResponse:
    """
    Create a new group circle. The authenticated user is automatically
    assigned as the owner member.
    """
    group = Group(name=payload.name, owner_id=current_user.id)
    db.add(group)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create group due to a constraint violation",
        ) from None

    db.refresh(group)
    return GroupResponse.model_validate(group)


@router.get(
    "",
    response_model=list[GroupResponse],
    summary="List groups the authenticated user belongs to",
)
def list_groups(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[GroupResponse]:
    """
    Return all group circles in which the current user holds active membership,
    ordered by creation date descending.
    """
    groups = (
        db.execute(
            select(Group)
            .join(GroupMembership, GroupMembership.group_id == Group.id)
            .where(GroupMembership.user_id == current_user.id)
            .order_by(Group.created_at.desc(), Group.id.desc())
        )
        .scalars()
        .all()
    )
    return [GroupResponse.model_validate(g) for g in groups]


@router.post(
    "/join",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Join a group via invite code",
)
def join_group(
    payload: GroupJoin,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> GroupResponse:
    """
    Join an existing group circle using its unique invite code.
    Rejects already-joined users with 409 Conflict.
    """
    group = db.execute(
        select(Group).where(Group.invite_code == payload.invite_code)
    ).scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found with the provided invite code",
        )

    # Check whether the user is already a member
    existing_membership = db.execute(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group.id,
            GroupMembership.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if existing_membership is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this group",
        )

    membership = GroupMembership(
        group_id=group.id,
        user_id=current_user.id,
        role=GroupRole.MEMBER.value,
    )
    db.add(membership)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this group",
        ) from None

    return GroupResponse.model_validate(group)


@router.get(
    "/{group_id}",
    response_model=GroupDetailResponse,
    summary="Get group details and member list",
)
def get_group(
    group_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> GroupDetailResponse:
    """
    Return group details and member list.
    Only active members of the group are authorized to view this resource.
    """
    group = db.execute(
        select(Group)
        .options(
            selectinload(Group.memberships).selectinload(GroupMembership.user)
        )
        .where(Group.id == group_id)
    ).scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    is_member = any(m.user_id == current_user.id for m in group.memberships)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this group",
        )

    return GroupDetailResponse.model_validate(group)
