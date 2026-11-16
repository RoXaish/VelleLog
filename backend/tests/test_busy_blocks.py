from datetime import datetime, time
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.busy_block import BusyBlock
from app.models.user import User


def _create_test_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash=hash_password("s3cure-passphrase"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ==============================================================================
# 1. Creation, Persistence & Properties
# ==============================================================================


def test_create_busy_block_success(db_session: Session) -> None:
    """A user can persist a recurring busy block with weekday, times, and timestamps."""
    user = _create_test_user(db_session, "busy_user@example.com")

    block = BusyBlock(
        user_id=user.id,
        weekday=0,  # Monday
        start_time=time(9, 30),
        end_time=time(11, 0),
        private_label="Dentist appointment",
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    assert block.id is not None
    assert block.user_id == user.id
    assert block.weekday == 0
    assert block.start_time == time(9, 30)
    assert block.end_time == time(11, 0)
    assert block.private_label == "Dentist appointment"
    assert isinstance(block.created_at, datetime)
    assert isinstance(block.updated_at, datetime)


def test_busy_block_optional_private_label(db_session: Session) -> None:
    """private_label is optional and defaults to None."""
    user = _create_test_user(db_session, "no_label@example.com")

    block = BusyBlock(
        user_id=user.id,
        weekday=4,  # Friday
        start_time=time(14, 0),
        end_time=time(16, 0),
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    assert block.private_label is None


def test_busy_blocks_user_relationship_and_ordering(db_session: Session) -> None:
    """Blocks belong to the individual user and order by weekday and start_time."""
    user = _create_test_user(db_session, "schedule_user@example.com")

    # Add blocks out of chronological order
    b1 = BusyBlock(user_id=user.id, weekday=3, start_time=time(15, 0), end_time=time(16, 0))
    b2 = BusyBlock(user_id=user.id, weekday=1, start_time=time(9, 0), end_time=time(10, 0))
    b3 = BusyBlock(user_id=user.id, weekday=1, start_time=time(13, 0), end_time=time(14, 0))

    db_session.add_all([b1, b2, b3])
    db_session.commit()
    db_session.refresh(user)

    assert len(user.busy_blocks) == 3
    # Check ordering: Tuesday 09:00, Tuesday 13:00, Thursday 15:00
    assert [(b.weekday, b.start_time) for b in user.busy_blocks] == [
        (1, time(9, 0)),
        (1, time(13, 0)),
        (3, time(15, 0)),
    ]


# ==============================================================================
# 2. Weekday Range Validation (0–6, Monday–Sunday)
# ==============================================================================


@pytest.mark.parametrize("valid_weekday", [0, 1, 2, 3, 4, 5, 6])
def test_valid_weekday_accepted(db_session: Session, valid_weekday: int) -> None:
    """All weekdays from 0 (Monday) to 6 (Sunday) are valid."""
    user = _create_test_user(db_session, f"weekday_{valid_weekday}@example.com")

    block = BusyBlock(
        user_id=user.id,
        weekday=valid_weekday,
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    db_session.add(block)
    db_session.commit()
    assert block.id is not None


@pytest.mark.parametrize("invalid_weekday", [-1, 7, 8, 100, -10])
def test_invalid_weekday_raises_value_error(db_session: Session, invalid_weekday: int) -> None:
    """Weekdays outside 0–6 raise ValueError in Python."""
    user = _create_test_user(db_session, f"inv_wk_{invalid_weekday}@example.com")

    with pytest.raises(ValueError, match="weekday must be an integer between 0"):
        BusyBlock(
            user_id=user.id,
            weekday=invalid_weekday,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )


def test_invalid_weekday_type_rejected() -> None:
    """Non-integer weekday raises ValueError."""
    with pytest.raises(ValueError, match="weekday must be an integer between 0"):
        BusyBlock(
            user_id=1,
            weekday="Monday",  # type: ignore
            start_time=time(10, 0),
            end_time=time(11, 0),
        )


# ==============================================================================
# 3. Time Range Validation (start_time < end_time)
# ==============================================================================


def test_start_time_equal_to_end_time_raises_value_error() -> None:
    """Equal start and end times raise ValueError."""
    with pytest.raises(ValueError, match="must be strictly (earlier|later)"):
        BusyBlock(
            user_id=1,
            weekday=0,
            start_time=time(10, 0),
            end_time=time(10, 0),
        )


def test_start_time_later_than_end_time_raises_value_error() -> None:
    """Inverted start and end times raise ValueError."""
    with pytest.raises(ValueError, match="must be strictly (earlier|later)"):
        BusyBlock(
            user_id=1,
            weekday=0,
            start_time=time(14, 0),
            end_time=time(13, 0),
        )


def test_modifying_time_to_invalid_range_raises_value_error(db_session: Session) -> None:
    """Modifying start_time or end_time after instantiation raises ValueError if invalid."""
    user = _create_test_user(db_session, "modify_user@example.com")
    block = BusyBlock(
        user_id=user.id,
        weekday=2,
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    db_session.add(block)
    db_session.commit()

    with pytest.raises(ValueError, match="start_time .* must be strictly earlier than end_time"):
        block.start_time = time(12, 0)

    with pytest.raises(ValueError, match="end_time .* must be strictly later than start_time"):
        block.end_time = time(8, 0)


# ==============================================================================
# 4. Database-Level Constraint Enforcement
# ==============================================================================


def test_database_rejects_invalid_time_range(db_session: Session) -> None:
    """Bypassing Python validation still violates database check constraint."""
    user = _create_test_user(db_session, "db_time_user@example.com")

    # Bypass Python-level validator by writing directly to __dict__
    block = BusyBlock(
        user_id=user.id,
        weekday=1,
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    db_session.add(block)
    db_session.flush()

    # Force database update with inverted time range
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE busy_blocks SET start_time = '12:00:00', end_time = '10:00:00' WHERE id = :id"),
            {"id": block.id},
        )
        db_session.commit()

    db_session.rollback()


def test_database_rejects_invalid_weekday(db_session: Session) -> None:
    """Direct database insert with weekday outside 0-6 violates check constraint."""
    user = _create_test_user(db_session, "db_wk_user@example.com")

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO busy_blocks (user_id, weekday, start_time, end_time, created_at, updated_at) "
                "VALUES (:user_id, 7, '09:00:00', '10:00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"user_id": user.id},
        )
        db_session.commit()

    db_session.rollback()


# ==============================================================================
# 5. Foreign Key & Cascade Delete
# ==============================================================================


def test_foreign_key_invalid_user_id_rejected(db_session: Session) -> None:
    """Non-existent user_id violates foreign key constraint."""
    non_existent_user_id = 999_999
    block = BusyBlock(
        user_id=non_existent_user_id,
        weekday=0,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    db_session.add(block)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_cascade_delete_user_removes_busy_blocks(db_session: Session) -> None:
    """Deleting a user removes all their associated busy blocks."""
    user = _create_test_user(db_session, "cascade_bb_user@example.com")
    user_id = user.id

    b1 = BusyBlock(user_id=user_id, weekday=0, start_time=time(9, 0), end_time=time(10, 0))
    b2 = BusyBlock(user_id=user_id, weekday=2, start_time=time(14, 0), end_time=time(15, 0))
    db_session.add_all([b1, b2])
    db_session.commit()

    # Delete user
    db_session.delete(user)
    db_session.commit()

    # Verify no orphan busy blocks remain
    remaining = db_session.execute(
        select(BusyBlock).where(BusyBlock.user_id == user_id)
    ).scalars().all()
    assert len(remaining) == 0
