from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CsrfProtectedUser, CurrentUser
from app.db.session import get_db
from app.models.schedule_exception import ScheduleException
from app.schemas.schedule_exception import (
    ScheduleExceptionCreate,
    ScheduleExceptionResponse,
    ScheduleExceptionUpdate,
)

router = APIRouter(prefix="/schedule-exceptions", tags=["schedule-exceptions"])


@router.post(
    "",
    response_model=ScheduleExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new one-off schedule exception",
)
def create_schedule_exception(
    payload: ScheduleExceptionCreate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> ScheduleExceptionResponse:
    """
    Create a new schedule exception ('busy' or 'free') for the authenticated user
    on a specific date.
    """
    exception = ScheduleException(
        user_id=current_user.id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        exception_type=payload.exception_type,
        private_label=payload.private_label,
    )
    db.add(exception)
    db.commit()
    db.refresh(exception)
    return ScheduleExceptionResponse.model_validate(exception)


@router.get(
    "",
    response_model=list[ScheduleExceptionResponse],
    summary="List the authenticated user's schedule exceptions",
)
def list_schedule_exceptions(
    current_user: CurrentUser,
    date: date | None = Query(None, description="Filter exceptions on a specific date"),
    start_date: date | None = Query(None, description="Filter exceptions on or after this date"),
    end_date: date | None = Query(None, description="Filter exceptions on or before this date"),
    db: Session = Depends(get_db),
) -> list[ScheduleExceptionResponse]:
    """
    Return all schedule exceptions belonging to the authenticated user,
    ordered chronologically by date and start_time.
    """
    stmt = (
        select(ScheduleException)
        .where(ScheduleException.user_id == current_user.id)
        .order_by(ScheduleException.date.asc(), ScheduleException.start_time.asc())
    )
    if date is not None:
        stmt = stmt.where(ScheduleException.date == date)
    if start_date is not None:
        stmt = stmt.where(ScheduleException.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ScheduleException.date <= end_date)

    exceptions = db.execute(stmt).scalars().all()
    return [ScheduleExceptionResponse.model_validate(e) for e in exceptions]


@router.patch(
    "/{exception_id}",
    response_model=ScheduleExceptionResponse,
    summary="Update an existing schedule exception",
)
def update_schedule_exception(
    exception_id: int,
    payload: ScheduleExceptionUpdate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> ScheduleExceptionResponse:
    """
    Update fields of an existing schedule exception.
    Only the exception's owner is permitted to modify it.
    """
    exception = db.get(ScheduleException, exception_id)
    if exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule exception not found",
        )

    if exception.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this schedule exception",
        )

    # Validate resulting time range
    new_start = payload.start_time if payload.start_time is not None else exception.start_time
    new_end = payload.end_time if payload.end_time is not None else exception.end_time
    if new_start >= new_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time must be strictly earlier than end_time",
        )

    if payload.date is not None:
        exception.date = payload.date
    if payload.exception_type is not None:
        exception.exception_type = payload.exception_type

    exception.start_time = new_start
    exception.end_time = new_end

    if "private_label" in payload.model_fields_set:
        exception.private_label = payload.private_label

    db.commit()
    db.refresh(exception)
    return ScheduleExceptionResponse.model_validate(exception)


@router.delete(
    "/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a schedule exception",
)
def delete_schedule_exception(
    exception_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> Response:
    """
    Delete a schedule exception.
    Only the exception's owner is permitted to delete it.
    """
    exception = db.get(ScheduleException, exception_id)
    if exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule exception not found",
        )

    if exception.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this schedule exception",
        )

    db.delete(exception)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
