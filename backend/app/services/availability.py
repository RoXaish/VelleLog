from datetime import date, datetime, time, timedelta, timezone
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.busy_block import BusyBlock
from app.models.group import Group, GroupMembership
from app.schemas.availability import AvailabilitySlotResponse, MemberAvailabilityNow

# Asia/Kolkata timezone (UTC+05:30)
try:
    from zoneinfo import ZoneInfo
    KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


def time_to_seconds(t: time) -> int:
    """Convert a datetime.time to elapsed seconds from midnight."""
    return t.hour * 3600 + t.minute * 60 + t.second


def seconds_to_time(s: int) -> time:
    """Convert elapsed seconds from midnight to a datetime.time object."""
    if s >= 86400:
        return time(23, 59, 59)
    hours = s // 3600
    minutes = (s % 3600) // 60
    seconds = s % 60
    return time(hours, minutes, seconds)


def merge_intervals(intervals: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping and contiguous intervals [start, end]."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged = [sorted_intervals[0]]
    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def _get_group_for_member(db: Session, group_id: int, current_user_id: int) -> Group:
    """
    Fetch a group with memberships and users loaded, verifying that the group
    exists and that the requesting user holds active membership.
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

    is_member = any(m.user_id == current_user_id for m in group.memberships)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this group",
        )

    return group


def get_group_availability_now(
    db: Session,
    group_id: int,
    current_user_id: int,
    current_datetime: datetime | None = None,
) -> list[MemberAvailabilityNow]:
    """
    Determine whether each group member is currently 'free' or 'busy'
    based on their recurring BusyBlocks in the Asia/Kolkata timezone.
    Private labels and sensitive schedule data are never exposed.
    """
    group = _get_group_for_member(db, group_id, current_user_id)

    # Determine current timestamp in Asia/Kolkata
    if current_datetime is not None:
        if current_datetime.tzinfo is None:
            now_kolkata = current_datetime.replace(tzinfo=KOLKATA_TZ)
        else:
            now_kolkata = current_datetime.astimezone(KOLKATA_TZ)
    else:
        now_kolkata = datetime.now(KOLKATA_TZ)

    current_weekday = now_kolkata.weekday()
    current_time = now_kolkata.time()

    member_ids = [m.user_id for m in group.memberships]

    # Query busy blocks for group members on current weekday
    busy_blocks = (
        db.execute(
            select(BusyBlock).where(
                BusyBlock.user_id.in_(member_ids),
                BusyBlock.weekday == current_weekday,
                BusyBlock.start_time <= current_time,
                BusyBlock.end_time > current_time,
            )
        )
        .scalars()
        .all()
    )

    busy_user_ids = {b.user_id for b in busy_blocks}

    results = []
    # Sort members by user_id for deterministic order
    sorted_memberships = sorted(group.memberships, key=lambda m: m.user_id)
    for membership in sorted_memberships:
        status_value = "busy" if membership.user_id in busy_user_ids else "free"
        results.append(
            MemberAvailabilityNow(
                user_id=membership.user_id,
                email=membership.user.email,
                status=status_value,
            )
        )

    return results


def get_group_availability_slots(
    db: Session,
    group_id: int,
    current_user_id: int,
    target_date: date,
    min_duration_minutes: int = 30,
    min_free_members: int | None = None,
) -> list[AvailabilitySlotResponse]:
    """
    Calculate matching common free-time windows for a group on a given date.
    Considers recurring BusyBlocks, merges overlapping intervals, and enforces
    minimum duration and minimum free members constraints.
    """
    if min_duration_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="minimum duration must be at least 1 minute",
        )

    if min_free_members is not None and min_free_members <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="minimum number of free members must be at least 1",
        )

    group = _get_group_for_member(db, group_id, current_user_id)

    member_ids = sorted([m.user_id for m in group.memberships])
    total_members = len(member_ids)

    required_free = min_free_members if min_free_members is not None else total_members

    if required_free > total_members:
        return []

    target_weekday = target_date.weekday()

    # Query all recurring busy blocks for members on this weekday
    blocks = (
        db.execute(
            select(BusyBlock).where(
                BusyBlock.user_id.in_(member_ids),
                BusyBlock.weekday == target_weekday,
            )
        )
        .scalars()
        .all()
    )

    # Group and merge busy intervals per user
    user_busy_raw: dict[int, list[tuple[int, int]]] = {uid: [] for uid in member_ids}
    for block in blocks:
        s_sec = time_to_seconds(block.start_time)
        e_sec = time_to_seconds(block.end_time)
        user_busy_raw[block.user_id].append((s_sec, e_sec))

    user_busy_merged = {
        uid: merge_intervals(intervals) for uid, intervals in user_busy_raw.items()
    }

    # Collect boundary points across the entire day [0, 86400]
    points = {0, 86400}
    for intervals in user_busy_merged.values():
        for s, e in intervals:
            points.add(max(0, min(86400, s)))
            points.add(max(0, min(86400, e)))

    sorted_points = sorted(points)

    # Build elementary intervals with their set of free members
    elementary: list[tuple[int, int, set[int]]] = []
    for i in range(len(sorted_points) - 1):
        p_start, p_end = sorted_points[i], sorted_points[i + 1]
        mid = (p_start + p_end) / 2.0
        free_members = {
            uid
            for uid, intervals in user_busy_merged.items()
            if not any(s <= mid < e for s, e in intervals)
        }
        elementary.append((p_start, p_end, free_members))

    # Merge elementary intervals into maximal continuous windows where
    # at least required_free members are free throughout
    slots: list[AvailabilitySlotResponse] = []
    curr_start: int | None = None
    curr_end: int | None = None
    curr_free: set[int] | None = None

    def _flush_current_window() -> None:
        nonlocal curr_start, curr_end, curr_free
        if curr_start is not None and curr_end is not None and curr_free is not None:
            dur = (curr_end - curr_start) // 60
            if dur >= min_duration_minutes and len(curr_free) >= required_free:
                slots.append(
                    AvailabilitySlotResponse(
                        start_time=seconds_to_time(curr_start),
                        end_time=seconds_to_time(curr_end),
                        duration_minutes=dur,
                        free_members_count=len(curr_free),
                        free_member_ids=sorted(list(curr_free)),
                    )
                )
        curr_start = None
        curr_end = None
        curr_free = None

    for p_start, p_end, free_set in elementary:
        if len(free_set) < required_free:
            _flush_current_window()
        else:
            if curr_start is None:
                curr_start = p_start
                curr_end = p_end
                curr_free = set(free_set)
            else:
                common = curr_free & free_set
                if len(common) >= required_free:
                    curr_end = p_end
                    curr_free = common
                else:
                    _flush_current_window()
                    curr_start = p_start
                    curr_end = p_end
                    curr_free = set(free_set)

    _flush_current_window()
    return slots
