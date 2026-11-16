from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.busy_block import BusyBlock
from app.schemas.busy_block import (
    BusyBlockCopyDay,
    BusyBlockCreate,
    BusyBlockResponse,
    BusyBlockUpdate,
)

router = APIRouter(prefix="/busy-blocks", tags=["busy-blocks"])


@router.post(
    "",
    response_model=BusyBlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new weekly busy block",
)
def create_busy_block(
    payload: BusyBlockCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BusyBlockResponse:
    """
    Create a recurring weekly busy time block for the authenticated user.
    """
    block = BusyBlock(
        user_id=current_user.id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        private_label=payload.private_label,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return BusyBlockResponse.model_validate(block)


@router.get(
    "",
    response_model=list[BusyBlockResponse],
    summary="List the authenticated user's busy blocks",
)
def list_busy_blocks(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[BusyBlockResponse]:
    """
    Return all weekly recurring busy blocks belonging to the authenticated user,
    ordered chronologically by weekday (0=Monday..6=Sunday) and start_time.
    """
    blocks = (
        db.execute(
            select(BusyBlock)
            .where(BusyBlock.user_id == current_user.id)
            .order_by(BusyBlock.weekday.asc(), BusyBlock.start_time.asc())
        )
        .scalars()
        .all()
    )
    return [BusyBlockResponse.model_validate(b) for b in blocks]


@router.post(
    "/copy-day",
    response_model=list[BusyBlockResponse],
    status_code=status.HTTP_200_OK,
    summary="Copy all busy blocks from one weekday to another",
)
def copy_day_busy_blocks(
    payload: BusyBlockCopyDay,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[BusyBlockResponse]:
    """
    Copy all recurring blocks from source_weekday to target_weekday.
    Existing blocks on target_weekday are replaced in a single transaction.
    Private labels are preserved.
    """
    # 1. Fetch source blocks for the authenticated user
    source_blocks = (
        db.execute(
            select(BusyBlock)
            .where(
                BusyBlock.user_id == current_user.id,
                BusyBlock.weekday == payload.source_weekday,
            )
            .order_by(BusyBlock.start_time.asc())
        )
        .scalars()
        .all()
    )

    # 2. Delete existing blocks on target weekday
    db.execute(
        delete(BusyBlock).where(
            BusyBlock.user_id == current_user.id,
            BusyBlock.weekday == payload.target_weekday,
        )
    )

    # 3. Create copies for the target weekday
    copied_blocks = [
        BusyBlock(
            user_id=current_user.id,
            weekday=payload.target_weekday,
            start_time=sb.start_time,
            end_time=sb.end_time,
            private_label=sb.private_label,
        )
        for sb in source_blocks
    ]
    if copied_blocks:
        db.add_all(copied_blocks)

    db.commit()

    for b in copied_blocks:
        db.refresh(b)

    return [BusyBlockResponse.model_validate(b) for b in copied_blocks]


@router.patch(
    "/{block_id}",
    response_model=BusyBlockResponse,
    summary="Update an existing busy block",
)
def update_busy_block(
    block_id: int,
    payload: BusyBlockUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> BusyBlockResponse:
    """
    Update fields of an existing busy block.
    Only the block's owner is permitted to modify it.
    """
    block = db.get(BusyBlock, block_id)
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Busy block not found",
        )

    if block.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this busy block",
        )

    # Validate resulting time range
    new_start = payload.start_time if payload.start_time is not None else block.start_time
    new_end = payload.end_time if payload.end_time is not None else block.end_time
    if new_start >= new_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time must be strictly earlier than end_time",
        )

    if payload.weekday is not None:
        block.weekday = payload.weekday

    block.start_time = new_start
    block.end_time = new_end

    if "private_label" in payload.model_fields_set:
        block.private_label = payload.private_label

    db.commit()
    db.refresh(block)
    return BusyBlockResponse.model_validate(block)


@router.delete(
    "/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a busy block",
)
def delete_busy_block(
    block_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    """
    Delete a busy block.
    Only the block's owner is permitted to delete it.
    """
    block = db.get(BusyBlock, block_id)
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Busy block not found",
        )

    if block.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this busy block",
        )

    db.delete(block)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
