from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CsrfProtectedUser, CurrentUser
from app.db.session import get_db
from app.models.group import Group, GroupMembership
from app.models.schedule_template import (
    AppliedScheduleTemplate,
    ScheduleTemplate,
    TemplateBusyBlock,
)
from app.schemas.schedule_template import (
    AppliedTemplateResponse,
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    ScheduleTemplateUpdate,
    TemplateBusyBlockCreate,
    TemplateBusyBlockResponse,
    TemplateBusyBlockUpdate,
)

router = APIRouter(prefix="/groups/{group_id}/templates", tags=["templates"])


def _ensure_group_member(db: Session, group_id: int, user_id: int) -> Group:
    """
    Ensure the group exists and that the user is an active member of that group.
    Raises 404 if the group is missing, or 403 if the user is not a member.
    """
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    membership = db.execute(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this group",
        )

    return group


def _get_template_for_group(db: Session, group_id: int, template_id: int) -> ScheduleTemplate:
    """Fetch template ensuring it belongs to the given group, or raise 404."""
    template = db.execute(
        select(ScheduleTemplate)
        .options(selectinload(ScheduleTemplate.blocks))
        .where(
            ScheduleTemplate.id == template_id,
            ScheduleTemplate.group_id == group_id,
        )
    ).scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule template not found",
        )
    return template


# ==============================================================================
# 1. Template CRUD
# ==============================================================================


@router.post(
    "",
    response_model=ScheduleTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shared schedule template for a group circle",
)
def create_schedule_template(
    group_id: int,
    payload: ScheduleTemplateCreate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> ScheduleTemplateResponse:
    """
    Create a new timetable template for the specified group circle.
    Optionally accepts an initial list of template busy blocks.
    """
    _ensure_group_member(db, group_id, current_user.id)

    template = ScheduleTemplate(
        group_id=group_id,
        name=payload.name,
        created_by_user_id=current_user.id,
    )

    for block_data in payload.blocks:
        template.blocks.append(
            TemplateBusyBlock(
                weekday=block_data.weekday,
                start_time=block_data.start_time,
                end_time=block_data.end_time,
            )
        )

    db.add(template)
    db.commit()
    db.refresh(template)

    response = ScheduleTemplateResponse.model_validate(template)
    response.is_applied = False
    return response


@router.get(
    "",
    response_model=list[ScheduleTemplateResponse],
    summary="List all shared schedule templates for a group circle",
)
def list_schedule_templates(
    group_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[ScheduleTemplateResponse]:
    """
    Return all templates belonging to the group, including their blocks
    and an `is_applied` flag showing whether the authenticated user has applied each.
    """
    _ensure_group_member(db, group_id, current_user.id)

    templates = (
        db.execute(
            select(ScheduleTemplate)
            .options(selectinload(ScheduleTemplate.blocks))
            .where(ScheduleTemplate.group_id == group_id)
            .order_by(ScheduleTemplate.created_at.asc(), ScheduleTemplate.id.asc())
        )
        .scalars()
        .all()
    )

    applied_ids = set(
        db.execute(
            select(AppliedScheduleTemplate.template_id).where(
                AppliedScheduleTemplate.user_id == current_user.id
            )
        )
        .scalars()
        .all()
    )

    results = []
    for t in templates:
        resp = ScheduleTemplateResponse.model_validate(t)
        resp.is_applied = t.id in applied_ids
        results.append(resp)

    return results


@router.get(
    "/{template_id}",
    response_model=ScheduleTemplateResponse,
    summary="Get details of a specific schedule template",
)
def get_schedule_template(
    group_id: int,
    template_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ScheduleTemplateResponse:
    """Return a single template with its blocks and user application status."""
    _ensure_group_member(db, group_id, current_user.id)
    template = _get_template_for_group(db, group_id, template_id)

    is_applied = db.execute(
        select(AppliedScheduleTemplate.id).where(
            AppliedScheduleTemplate.user_id == current_user.id,
            AppliedScheduleTemplate.template_id == template_id,
        )
    ).scalar_one_or_none() is not None

    resp = ScheduleTemplateResponse.model_validate(template)
    resp.is_applied = is_applied
    return resp


@router.patch(
    "/{template_id}",
    response_model=ScheduleTemplateResponse,
    summary="Rename an existing schedule template",
)
def update_schedule_template(
    group_id: int,
    template_id: int,
    payload: ScheduleTemplateUpdate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> ScheduleTemplateResponse:
    """Rename a schedule template. Accessible to all group members."""
    _ensure_group_member(db, group_id, current_user.id)
    template = _get_template_for_group(db, group_id, template_id)

    template.name = payload.name
    db.commit()
    db.refresh(template)

    is_applied = db.execute(
        select(AppliedScheduleTemplate.id).where(
            AppliedScheduleTemplate.user_id == current_user.id,
            AppliedScheduleTemplate.template_id == template_id,
        )
    ).scalar_one_or_none() is not None

    resp = ScheduleTemplateResponse.model_validate(template)
    resp.is_applied = is_applied
    return resp


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a schedule template and all its blocks",
)
def delete_schedule_template(
    group_id: int,
    template_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> None:
    """Delete a schedule template. Accessible to group members."""
    _ensure_group_member(db, group_id, current_user.id)
    template = _get_template_for_group(db, group_id, template_id)

    db.delete(template)
    db.commit()


# ==============================================================================
# 2. Template Busy Blocks CRUD
# ==============================================================================


@router.post(
    "/{template_id}/blocks",
    response_model=TemplateBusyBlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a busy block to a schedule template",
)
def add_template_busy_block(
    group_id: int,
    template_id: int,
    payload: TemplateBusyBlockCreate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> TemplateBusyBlockResponse:
    """Add a new weekly busy time window to an existing schedule template."""
    _ensure_group_member(db, group_id, current_user.id)
    _get_template_for_group(db, group_id, template_id)

    block = TemplateBusyBlock(
        template_id=template_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(block)
    db.commit()
    db.refresh(block)

    return TemplateBusyBlockResponse.model_validate(block)


@router.patch(
    "/{template_id}/blocks/{block_id}",
    response_model=TemplateBusyBlockResponse,
    summary="Update a busy block in a schedule template",
)
def update_template_busy_block(
    group_id: int,
    template_id: int,
    block_id: int,
    payload: TemplateBusyBlockUpdate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> TemplateBusyBlockResponse:
    """Modify the weekday or time range of an existing template busy block."""
    _ensure_group_member(db, group_id, current_user.id)
    _get_template_for_group(db, group_id, template_id)

    block = db.execute(
        select(TemplateBusyBlock).where(
            TemplateBusyBlock.id == block_id,
            TemplateBusyBlock.template_id == template_id,
        )
    ).scalar_one_or_none()

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template busy block not found",
        )

    new_start = payload.start_time if payload.start_time is not None else block.start_time
    new_end = payload.end_time if payload.end_time is not None else block.end_time

    if new_start >= new_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time must be strictly earlier than end_time",
        )

    if payload.weekday is not None:
        block.weekday = payload.weekday
    if payload.start_time is not None:
        block.start_time = payload.start_time
    if payload.end_time is not None:
        block.end_time = payload.end_time

    db.commit()
    db.refresh(block)
    return TemplateBusyBlockResponse.model_validate(block)


@router.delete(
    "/{template_id}/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a busy block from a schedule template",
)
def delete_template_busy_block(
    group_id: int,
    template_id: int,
    block_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> None:
    """Delete a busy block from a schedule template."""
    _ensure_group_member(db, group_id, current_user.id)
    _get_template_for_group(db, group_id, template_id)

    block = db.execute(
        select(TemplateBusyBlock).where(
            TemplateBusyBlock.id == block_id,
            TemplateBusyBlock.template_id == template_id,
        )
    ).scalar_one_or_none()

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template busy block not found",
        )

    db.delete(block)
    db.commit()


# ==============================================================================
# 3. Applying and Removing Templates
# ==============================================================================


@router.post(
    "/{template_id}/apply",
    response_model=AppliedTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply a template to the authenticated user's recurring schedule",
)
def apply_template_to_schedule(
    group_id: int,
    template_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> AppliedTemplateResponse:
    """
    Apply a shared timetable template to the user's recurring schedule.
    Prevents duplicate application (returns 409 Conflict if already applied).
    Preserves all personal BusyBlocks.
    """
    _ensure_group_member(db, group_id, current_user.id)
    _get_template_for_group(db, group_id, template_id)

    # Check if already applied
    existing = db.execute(
        select(AppliedScheduleTemplate).where(
            AppliedScheduleTemplate.user_id == current_user.id,
            AppliedScheduleTemplate.template_id == template_id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template is already applied to your schedule",
        )

    application = AppliedScheduleTemplate(
        user_id=current_user.id,
        template_id=template_id,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return AppliedTemplateResponse.model_validate(application)


@router.delete(
    "/{template_id}/apply",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an applied template from the authenticated user's schedule",
)
def remove_template_from_schedule(
    group_id: int,
    template_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Remove an applied timetable template from the user's schedule safely.
    Personal BusyBlocks remain completely untouched.
    """
    _ensure_group_member(db, group_id, current_user.id)
    _get_template_for_group(db, group_id, template_id)

    application = db.execute(
        select(AppliedScheduleTemplate).where(
            AppliedScheduleTemplate.user_id == current_user.id,
            AppliedScheduleTemplate.template_id == template_id,
        )
    ).scalar_one_or_none()

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template is not applied to your schedule",
        )

    db.delete(application)
    db.commit()
