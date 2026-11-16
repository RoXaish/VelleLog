from datetime import date, datetime, time, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.busy_block import BusyBlock
from app.models.group import Group, GroupMembership
from app.models.schedule_exception import ScheduleException
from app.models.user import User
from app.services.availability import (
    KOLKATA_TZ,
    get_group_availability_now,
    get_group_availability_slots,
)

EXCEPTIONS_URL = "/api/schedule-exceptions"
REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
GROUPS_URL = "/api/groups"
RAW_PASSWORD = "s3cure-passphrase"


def _create_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash=hash_password(RAW_PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register_and_login(
    client: TestClient,
    email: str = "ex_user@example.com",
    password: str = RAW_PASSWORD,
) -> tuple[dict, str]:
    registered = client.post(
        REGISTER_URL,
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201

    logged_in = client.post(
        LOGIN_URL,
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200
    return registered.json(), logged_in.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Model Unit Tests
# ==============================================================================


def test_schedule_exception_model_create_success(db_session: Session) -> None:
    """ScheduleException persists date, time range, type, optional label, and timestamps."""
    user = _create_user(db_session, "ex_model_1@example.com")

    exception = ScheduleException(
        user_id=user.id,
        date=date(2026, 11, 20),
        start_time=time(9, 0),
        end_time=time(11, 30),
        exception_type="busy",
        private_label="Dentist visit",
    )
    db_session.add(exception)
    db_session.commit()
    db_session.refresh(exception)

    assert exception.id is not None
    assert exception.user_id == user.id
    assert exception.date == date(2026, 11, 20)
    assert exception.start_time == time(9, 0)
    assert exception.end_time == time(11, 30)
    assert exception.exception_type == "busy"
    assert exception.private_label == "Dentist visit"
    assert isinstance(exception.created_at, datetime)
    assert isinstance(exception.updated_at, datetime)


def test_schedule_exception_model_optional_label(db_session: Session) -> None:
    """private_label is optional and defaults to None."""
    user = _create_user(db_session, "ex_model_2@example.com")

    exception = ScheduleException(
        user_id=user.id,
        date=date(2026, 11, 21),
        start_time=time(14, 0),
        end_time=time(16, 0),
        exception_type="free",
    )
    db_session.add(exception)
    db_session.commit()
    db_session.refresh(exception)

    assert exception.private_label is None
    assert exception.exception_type == "free"


def test_schedule_exception_model_invalid_time_range(db_session: Session) -> None:
    """start_time must be strictly earlier than end_time."""
    user = _create_user(db_session, "ex_model_3@example.com")

    # start_time == end_time
    with pytest.raises(ValueError, match="strictly later"):
        ScheduleException(
            user_id=user.id,
            date=date(2026, 11, 20),
            start_time=time(10, 0),
            end_time=time(10, 0),
            exception_type="busy",
        )

    # start_time > end_time
    with pytest.raises(ValueError, match="strictly later"):
        ScheduleException(
            user_id=user.id,
            date=date(2026, 11, 20),
            start_time=time(12, 0),
            end_time=time(10, 0),
            exception_type="busy",
        )


def test_schedule_exception_model_invalid_type(db_session: Session) -> None:
    """exception_type must be 'busy' or 'free'."""
    user = _create_user(db_session, "ex_model_4@example.com")

    with pytest.raises(ValueError, match="must be 'busy' or 'free'"):
        ScheduleException(
            user_id=user.id,
            date=date(2026, 11, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            exception_type="vacation",
        )


def test_schedule_exception_user_cascade_deletion(db_session: Session) -> None:
    """Deleting a user cascade-deletes their schedule exceptions."""
    user = _create_user(db_session, "ex_model_5@example.com")

    ex = ScheduleException(
        user_id=user.id,
        date=date(2026, 11, 20),
        start_time=time(10, 0),
        end_time=time(11, 0),
        exception_type="busy",
    )
    db_session.add(ex)
    db_session.commit()
    ex_id = ex.id

    db_session.delete(user)
    db_session.commit()

    deleted = db_session.get(ScheduleException, ex_id)
    assert deleted is None


# ==============================================================================
# 2. CRUD API Tests
# ==============================================================================


def test_api_schedule_exception_crud_flow(
    client: TestClient, db_session: Session
) -> None:
    """A user can create, list, update, and delete their schedule exceptions."""
    _, token = register_and_login(client, "ex_crud@example.com")
    headers = auth_header(token)

    # 1. Create busy exception
    create_res = client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "exception_type": "busy",
            "private_label": "Doctor appointment",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["date"] == "2026-11-20"
    assert created["start_time"] == "10:00:00"
    assert created["end_time"] == "12:00:00"
    assert created["exception_type"] == "busy"
    assert created["private_label"] == "Doctor appointment"
    ex_id = created["id"]

    # 2. Create free exception
    create_free = client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "15:00:00",
            "end_time": "16:00:00",
            "exception_type": "free",
        },
        headers=headers,
    )
    assert create_free.status_code == 201

    # 3. List exceptions
    list_res = client.get(EXCEPTIONS_URL, headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 2
    assert items[0]["id"] == ex_id
    assert items[1]["exception_type"] == "free"

    # 4. Filter by date
    filtered_res = client.get(f"{EXCEPTIONS_URL}?date=2026-11-20", headers=headers)
    assert filtered_res.status_code == 200
    assert len(filtered_res.json()) == 2

    empty_filter = client.get(f"{EXCEPTIONS_URL}?date=2026-11-25", headers=headers)
    assert empty_filter.status_code == 200
    assert len(empty_filter.json()) == 0

    # 5. Patch exception
    patch_res = client.patch(
        f"{EXCEPTIONS_URL}/{ex_id}",
        json={
            "start_time": "10:30:00",
            "private_label": "Rescheduled Doctor",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["start_time"] == "10:30:00"
    assert patched["private_label"] == "Rescheduled Doctor"

    # 6. Delete exception
    del_res = client.delete(f"{EXCEPTIONS_URL}/{ex_id}", headers=headers)
    assert del_res.status_code == 204

    # 7. Verify deletion
    list_after = client.get(EXCEPTIONS_URL, headers=headers).json()
    assert len(list_after) == 1
    assert list_after[0]["id"] != ex_id


def test_api_schedule_exception_validation_errors(
    client: TestClient, db_session: Session
) -> None:
    """Invalid requests produce 422 Unprocessable Entity."""
    _, token = register_and_login(client, "ex_val@example.com")
    headers = auth_header(token)

    # start_time >= end_time
    res1 = client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "12:00:00",
            "end_time": "11:00:00",
            "exception_type": "busy",
        },
        headers=headers,
    )
    assert res1.status_code == 422

    # invalid exception_type
    res2 = client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "exception_type": "holiday",
        },
        headers=headers,
    )
    assert res2.status_code == 422

    # PATCH with invalid time range
    create_res = client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "exception_type": "busy",
        },
        headers=headers,
    )
    ex_id = create_res.json()["id"]

    patch_invalid = client.patch(
        f"{EXCEPTIONS_URL}/{ex_id}",
        json={"start_time": "10:30:00"},  # now 10:30 > 10:00
        headers=headers,
    )
    assert patch_invalid.status_code == 422


def test_api_schedule_exception_ownership_isolation(
    client: TestClient, db_session: Session
) -> None:
    """Users cannot view, update, or delete other users' exceptions."""
    _, token_a = register_and_login(client, "user_a@example.com")
    _, token_b = register_and_login(client, "user_b@example.com")

    # User A creates an exception
    created = client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "09:00:00",
            "end_time": "11:00:00",
            "exception_type": "busy",
            "private_label": "User A Private Event",
        },
        headers=auth_header(token_a),
    ).json()
    ex_id = created["id"]

    # User B list does not see User A's exception
    list_b = client.get(EXCEPTIONS_URL, headers=auth_header(token_b)).json()
    assert len(list_b) == 0

    # User B cannot PATCH User A's exception (403 Forbidden)
    patch_res = client.patch(
        f"{EXCEPTIONS_URL}/{ex_id}",
        json={"private_label": "Hacked"},
        headers=auth_header(token_b),
    )
    assert patch_res.status_code == 403

    # User B cannot DELETE User A's exception (403 Forbidden)
    del_res = client.delete(
        f"{EXCEPTIONS_URL}/{ex_id}",
        headers=auth_header(token_b),
    )
    assert del_res.status_code == 403

    # Non-existent exception returns 404
    assert (
        client.patch(
            f"{EXCEPTIONS_URL}/999999",
            json={"private_label": "None"},
            headers=auth_header(token_a),
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"{EXCEPTIONS_URL}/999999",
            headers=auth_header(token_a),
        ).status_code
        == 404
    )


def test_api_schedule_exception_unauthenticated(client: TestClient) -> None:
    """Unauthenticated requests are rejected with 401."""
    client.cookies.clear()
    assert client.get(EXCEPTIONS_URL).status_code == 401
    assert client.post(EXCEPTIONS_URL, json={}).status_code == 401
    assert client.patch(f"{EXCEPTIONS_URL}/1", json={}).status_code == 401
    assert client.delete(f"{EXCEPTIONS_URL}/1").status_code == 401


# ==============================================================================
# 3. Availability Integration Tests
# ==============================================================================


def test_availability_now_busy_exception(
    client: TestClient, db_session: Session
) -> None:
    """A 'busy' exception marks an otherwise free user as busy in availability/now."""
    user_a, token_a = register_and_login(client, "avail_ex_now_a@example.com")
    user_b, token_b = register_and_login(client, "avail_ex_now_b@example.com")

    # Create group
    group = client.post(
        GROUPS_URL,
        json={"name": "Exception Circle"},
        headers=auth_header(token_a),
    ).json()

    # User B joins
    client.post(
        f"{GROUPS_URL}/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_b),
    )

    # 2026-11-20 is a Friday
    target_dt = datetime(2026, 11, 20, 10, 30, tzinfo=KOLKATA_TZ)

    # User A creates a busy exception on 2026-11-20 from 10:00 to 11:00
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "exception_type": "busy",
            "private_label": "Secret Interview",
        },
        headers=auth_header(token_a),
    )

    # Call availability/now at 10:30
    statuses = get_group_availability_now(
        db=db_session,
        group_id=group["id"],
        current_user_id=user_a["id"],
        current_datetime=target_dt,
    )
    status_map = {s.user_id: s.status for s in statuses}
    assert status_map[user_a["id"]] == "busy"
    assert status_map[user_b["id"]] == "free"


def test_availability_now_free_exception_overrides_recurring(
    client: TestClient, db_session: Session
) -> None:
    """A 'free' exception overrides a recurring busy block in availability/now."""
    user_a, token_a = register_and_login(client, "avail_ex_free_a@example.com")

    group = client.post(
        GROUPS_URL,
        json={"name": "Free Override Circle"},
        headers=auth_header(token_a),
    ).json()

    # User A has recurring busy block on Fridays (weekday=4) 09:00 - 17:00
    client.post(
        "/api/busy-blocks",
        json={
            "weekday": 4,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "private_label": "Work day",
        },
        headers=auth_header(token_a),
    )

    # Add free exception on 2026-11-20 (Friday) 12:00 - 14:00
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "12:00:00",
            "end_time": "14:00:00",
            "exception_type": "free",
        },
        headers=auth_header(token_a),
    )

    # Check at 13:00 (during free exception): should be FREE
    dt_free = datetime(2026, 11, 20, 13, 0, tzinfo=KOLKATA_TZ)
    res_free = get_group_availability_now(
        db=db_session,
        group_id=group["id"],
        current_user_id=user_a["id"],
        current_datetime=dt_free,
    )
    assert res_free[0].status == "free"

    # Check at 15:00 (outside free exception): should be BUSY
    dt_busy = datetime(2026, 11, 20, 15, 0, tzinfo=KOLKATA_TZ)
    res_busy = get_group_availability_now(
        db=db_session,
        group_id=group["id"],
        current_user_id=user_a["id"],
        current_datetime=dt_busy,
    )
    assert res_busy[0].status == "busy"


def test_availability_precedence_busy_over_free(
    client: TestClient, db_session: Session
) -> None:
    """When 'busy' and 'free' exceptions overlap, 'busy' takes precedence."""
    user_a, token_a = register_and_login(client, "precedence_a@example.com")

    group = client.post(
        GROUPS_URL,
        json={"name": "Precedence Circle"},
        headers=auth_header(token_a),
    ).json()

    # Recurring block: 09:00 to 17:00 on Friday (4)
    client.post(
        "/api/busy-blocks",
        json={"weekday": 4, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_header(token_a),
    )

    # Free exception: 10:00 to 14:00
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "14:00:00",
            "exception_type": "free",
        },
        headers=auth_header(token_a),
    )

    # Overlapping busy exception: 11:00 to 12:00
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "exception_type": "busy",
        },
        headers=auth_header(token_a),
    )

    # 1. At 10:30 (inside free, outside busy exception) -> free
    dt_1030 = datetime(2026, 11, 20, 10, 30, tzinfo=KOLKATA_TZ)
    res_1030 = get_group_availability_now(
        db=db_session,
        group_id=group["id"],
        current_user_id=user_a["id"],
        current_datetime=dt_1030,
    )
    assert res_1030[0].status == "free"

    # 2. At 11:30 (inside both free and busy exception) -> busy wins!
    dt_1130 = datetime(2026, 11, 20, 11, 30, tzinfo=KOLKATA_TZ)
    res_1130 = get_group_availability_now(
        db=db_session,
        group_id=group["id"],
        current_user_id=user_a["id"],
        current_datetime=dt_1130,
    )
    assert res_1130[0].status == "busy"

    # 3. At 13:00 (inside free, outside busy exception) -> free
    dt_1300 = datetime(2026, 11, 20, 13, 0, tzinfo=KOLKATA_TZ)
    res_1300 = get_group_availability_now(
        db=db_session,
        group_id=group["id"],
        current_user_id=user_a["id"],
        current_datetime=dt_1300,
    )
    assert res_1300[0].status == "free"


def test_availability_slots_with_exceptions(
    client: TestClient, db_session: Session
) -> None:
    """GET /api/groups/{id}/availability/slots reflects busy and free exceptions."""
    user_a, token_a = register_and_login(client, "slots_ex_a@example.com")
    user_b, token_b = register_and_login(client, "slots_ex_b@example.com")

    # Group
    group = client.post(
        GROUPS_URL,
        json={"name": "Slots Exception Group"},
        headers=auth_header(token_a),
    ).json()

    client.post(
        f"{GROUPS_URL}/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_b),
    )

    # 2026-11-20 is Friday (4)
    # User A is busy whole day 00:00 - 23:59:59 except for a free exception 14:00 - 16:00
    client.post(
        "/api/busy-blocks",
        json={"weekday": 4, "start_time": "00:00:00", "end_time": "23:59:59"},
        headers=auth_header(token_a),
    )
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "exception_type": "free",
        },
        headers=auth_header(token_a),
    )

    # User B has no recurring blocks, but has a busy exception 15:00 - 17:00
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "15:00:00",
            "end_time": "17:00:00",
            "exception_type": "busy",
        },
        headers=auth_header(token_b),
    )

    # Query common slots where both (2) members are free
    # User A is free 14:00 - 16:00
    # User B is free 00:00 - 15:00 and 17:00 - 24:00
    # Common free time: 14:00 to 15:00 (duration: 60 minutes)
    slots_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-20&min_duration_minutes=30",
        headers=auth_header(token_a),
    )
    assert slots_res.status_code == 200
    slots = slots_res.json()
    assert len(slots) == 1
    assert slots[0]["start_time"] == "14:00:00"
    assert slots[0]["end_time"] == "15:00:00"
    assert slots[0]["duration_minutes"] == 60
    assert slots[0]["free_members_count"] == 2


def test_availability_privacy_no_leak_of_exception_labels(
    client: TestClient, db_session: Session
) -> None:
    """Group members never see private labels or details of schedule exceptions."""
    user_a, token_a = register_and_login(client, "priv_ex_a@example.com")
    user_b, token_b = register_and_login(client, "priv_ex_b@example.com")

    # User A creates group
    group = client.post(
        GROUPS_URL,
        json={"name": "Privacy Guarded Group"},
        headers=auth_header(token_a),
    ).json()

    # User B joins
    client.post(
        f"{GROUPS_URL}/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_b),
    )

    # User A sets a highly sensitive private label on an exception
    client.post(
        EXCEPTIONS_URL,
        json={
            "date": "2026-11-20",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "exception_type": "busy",
            "private_label": "TOP_SECRET_THERAPY_SESSION",
        },
        headers=auth_header(token_a),
    )

    # User B queries availability/now
    now_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/now",
        headers=auth_header(token_b),
    )
    assert now_res.status_code == 200
    assert "TOP_SECRET" not in now_res.text
    for member in now_res.json():
        assert "private_label" not in member
        assert "label" not in member

    # User B queries availability/slots
    slots_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-20",
        headers=auth_header(token_b),
    )
    assert slots_res.status_code == 200
    assert "TOP_SECRET" not in slots_res.text
    for slot in slots_res.json():
        assert "private_label" not in slot
        assert "label" not in slot
