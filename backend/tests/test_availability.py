from datetime import date, datetime, time, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.busy_block import BusyBlock
from app.models.group import Group, GroupMembership
from app.models.user import User
from app.services.availability import (
    KOLKATA_TZ,
    get_group_availability_now,
    get_group_availability_slots,
    merge_intervals,
)

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
GROUPS_URL = "/api/groups"
RAW_PASSWORD = "s3cure-passphrase"


def register_and_login(
    client: TestClient,
    email: str = "avail_user@example.com",
    password: str = RAW_PASSWORD,
) -> tuple[dict, str]:
    """Helper to register and login a user."""
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
# 1. Authorization & Access Control (401, 403, 404)
# ==============================================================================


def test_availability_endpoints_require_authentication(
    client: TestClient, db_session: Session
) -> None:
    """Both availability endpoints reject unauthenticated requests with 401."""
    client.cookies.clear()
    assert client.get(f"{GROUPS_URL}/1/availability/now").status_code == 401
    assert client.get(f"{GROUPS_URL}/1/availability/slots?date=2026-11-16").status_code == 401


def test_availability_nonexistent_group_returns_404(
    client: TestClient, db_session: Session
) -> None:
    """Querying availability for an unknown group returns 404."""
    _, token = register_and_login(client, "avail_404@example.com")
    assert (
        client.get(
            f"{GROUPS_URL}/999999/availability/now", headers=auth_header(token)
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"{GROUPS_URL}/999999/availability/slots?date=2026-11-16",
            headers=auth_header(token),
        ).status_code
        == 404
    )


def test_availability_non_member_forbidden_403(
    client: TestClient, db_session: Session
) -> None:
    """Users who are not members of the group receive 403 Forbidden."""
    _, token_owner = register_and_login(client, "avail_owner@example.com")
    _, token_stranger = register_and_login(client, "avail_stranger@example.com")

    # Owner creates group
    group = client.post(
        GROUPS_URL,
        json={"name": "Private Availability Circle"},
        headers=auth_header(token_owner),
    ).json()

    # Stranger tries to query availability
    now_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/now",
        headers=auth_header(token_stranger),
    )
    assert now_res.status_code == 403
    assert "access denied" in now_res.json()["detail"].lower()

    slots_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-16",
        headers=auth_header(token_stranger),
    )
    assert slots_res.status_code == 403
    assert "access denied" in slots_res.json()["detail"].lower()


# ==============================================================================
# 2. Validation & Parameter Errors (422)
# ==============================================================================


def test_slots_missing_or_invalid_date_returns_422(
    client: TestClient, db_session: Session
) -> None:
    """Missing or non-ISO date string returns 422."""
    _, token = register_and_login(client, "val_slots_date@example.com")
    group = client.post(
        GROUPS_URL, json={"name": "Date Val Group"}, headers=auth_header(token)
    ).json()

    # Missing date
    assert (
        client.get(
            f"{GROUPS_URL}/{group['id']}/availability/slots",
            headers=auth_header(token),
        ).status_code
        == 422
    )

    # Malformed date
    assert (
        client.get(
            f"{GROUPS_URL}/{group['id']}/availability/slots?date=invalid-date",
            headers=auth_header(token),
        ).status_code
        == 422
    )


@pytest.mark.parametrize("bad_duration", [0, -1, -30])
def test_slots_invalid_duration_returns_422(
    client: TestClient, db_session: Session, bad_duration: int
) -> None:
    """Non-positive duration returns 422."""
    _, token = register_and_login(client, f"val_dur_{bad_duration}@example.com")
    group = client.post(
        GROUPS_URL, json={"name": "Dur Val Group"}, headers=auth_header(token)
    ).json()

    res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-16&min_duration={bad_duration}",
        headers=auth_header(token),
    )
    assert res.status_code == 422


@pytest.mark.parametrize("bad_members", [0, -1])
def test_slots_invalid_members_returns_422(
    client: TestClient, db_session: Session, bad_members: int
) -> None:
    """Non-positive min_free_members returns 422."""
    _, token = register_and_login(client, f"val_mem_{bad_members}@example.com")
    group = client.post(
        GROUPS_URL, json={"name": "Mem Val Group"}, headers=auth_header(token)
    ).json()

    res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-16&min_free_members={bad_members}",
        headers=auth_header(token),
    )
    assert res.status_code == 422


# ==============================================================================
# 3. GET /availability/now (Free / Busy Status & Privacy)
# ==============================================================================


def test_availability_now_and_privacy(client: TestClient, db_session: Session) -> None:
    """
    availability/now returns free or busy for each member.
    Never exposes private labels, passwords, or detailed schedule times.
    """
    user_a, token_a = register_and_login(client, "alice_now@example.com")
    user_b, token_b = register_and_login(client, "bob_now@example.com")

    # Alice creates group and Bob joins
    group = client.post(
        GROUPS_URL, json={"name": "Now Group"}, headers=auth_header(token_a)
    ).json()
    client.post(
        "/api/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_b),
    )

    # Add a busy block covering all day for Alice with a sensitive label
    secret_label = "CONFIDENTIAL_THERAPY_SESSION"
    db_session.add(
        BusyBlock(
            user_id=user_a["id"],
            weekday=datetime.now(KOLKATA_TZ).weekday(),
            start_time=time(0, 0),
            end_time=time(23, 59, 59),
            private_label=secret_label,
        )
    )
    db_session.commit()

    # Bob queries availability/now
    response = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/now",
        headers=auth_header(token_b),
    )
    assert response.status_code == 200
    members = response.json()

    assert len(members) == 2
    status_by_user = {m["user_id"]: m["status"] for m in members}
    assert status_by_user[user_a["id"]] == "busy"
    assert status_by_user[user_b["id"]] == "free"

    # Privacy verification: private_label and passwords must NEVER leak
    assert secret_label not in response.text
    assert "password" not in response.text
    assert "private_label" not in response.text


def test_availability_now_service_deterministic_time(db_session: Session) -> None:
    """The service accurately evaluates free/busy at specific simulated timestamps in Asia/Kolkata."""
    user1 = User(email="sim1@example.com", password_hash="hash")
    user2 = User(email="sim2@example.com", password_hash="hash")
    db_session.add_all([user1, user2])
    db_session.commit()

    group = Group(name="Sim Group", owner_id=user1.id)
    db_session.add(group)
    db_session.commit()
    db_session.add(
        GroupMembership(group_id=group.id, user_id=user2.id, role="member")
    )

    # User 1 is busy on Wednesday (weekday 2) from 10:00 to 12:00
    db_session.add(
        BusyBlock(
            user_id=user1.id,
            weekday=2,  # Wednesday
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
    )
    db_session.commit()

    # Test Wednesday at 10:30 IST -> user 1 is busy, user 2 is free
    dt_during = datetime(2026, 11, 18, 10, 30, tzinfo=KOLKATA_TZ)
    res_during = get_group_availability_now(
        db_session, group.id, user1.id, current_datetime=dt_during
    )
    status_map = {m.user_id: m.status for m in res_during}
    assert status_map[user1.id] == "busy"
    assert status_map[user2.id] == "free"

    # Test Wednesday at 12:30 IST -> both are free
    dt_after = datetime(2026, 11, 18, 12, 30, tzinfo=KOLKATA_TZ)
    res_after = get_group_availability_now(
        db_session, group.id, user1.id, current_datetime=dt_after
    )
    status_map_after = {m.user_id: m.status for m in res_after}
    assert status_map_after[user1.id] == "free"
    assert status_map_after[user2.id] == "free"


# ==============================================================================
# 4. GET /availability/slots (Overlapping Blocks, Timezone & Midnight Boundaries)
# ==============================================================================


def test_slots_overlapping_busy_blocks(client: TestClient, db_session: Session) -> None:
    """Overlapping busy blocks for a user are merged correctly into a single busy span."""
    user_a, token_a = register_and_login(client, "alice_overlap@example.com")
    user_b, token_b = register_and_login(client, "bob_overlap@example.com")

    # Create group with Alice & Bob
    group = client.post(
        GROUPS_URL, json={"name": "Overlap Group"}, headers=auth_header(token_a)
    ).json()
    client.post(
        "/api/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_b),
    )

    # Target date: Monday 2026-11-16 (weekday 0)
    # Alice has two overlapping blocks: 09:00-11:00 and 10:30-12:30 -> merged 09:00-12:30
    db_session.add_all(
        [
            BusyBlock(
                user_id=user_a["id"],
                weekday=0,
                start_time=time(9, 0),
                end_time=time(11, 0),
            ),
            BusyBlock(
                user_id=user_a["id"],
                weekday=0,
                start_time=time(10, 30),
                end_time=time(12, 30),
            ),
            # Bob has a busy block from 15:00 to 17:00
            BusyBlock(
                user_id=user_b["id"],
                weekday=0,
                start_time=time(15, 0),
                end_time=time(17, 0),
            ),
        ]
    )
    db_session.commit()

    # Query common slots for both members on Monday with min_duration=60
    res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-16&min_duration=60",
        headers=auth_header(token_a),
    )
    assert res.status_code == 200
    slots = res.json()

    # Expected common free windows:
    # 00:00:00 to 09:00:00 (540 min)
    # 12:30:00 to 15:00:00 (150 min)
    # 17:00:00 to 23:59:59 (419 min)
    assert len(slots) == 3
    assert slots[0]["start_time"] == "00:00:00"
    assert slots[0]["end_time"] == "09:00:00"
    assert slots[0]["free_members_count"] == 2

    assert slots[1]["start_time"] == "12:30:00"
    assert slots[1]["end_time"] == "15:00:00"
    assert slots[1]["duration_minutes"] == 150
    assert slots[1]["free_members_count"] == 2

    assert slots[2]["start_time"] == "17:00:00"
    assert slots[2]["end_time"] == "23:59:59"
    assert slots[2]["free_members_count"] == 2


def test_slots_midnight_and_day_boundaries(db_session: Session) -> None:
    """Schedules starting at midnight or ending at end-of-day are handled correctly."""
    user1 = User(email="mid1@example.com", password_hash="hash")
    user2 = User(email="mid2@example.com", password_hash="hash")
    db_session.add_all([user1, user2])
    db_session.commit()

    group = Group(name="Midnight Group", owner_id=user1.id)
    db_session.add(group)
    db_session.commit()
    db_session.add(
        GroupMembership(group_id=group.id, user_id=user2.id, role="member")
    )

    # Monday (weekday 0):
    # User 1 has overnight spill from Sunday (represented as 00:00 to 04:00 on Monday)
    # User 2 has night shift (20:00 to 23:59:59 on Monday)
    db_session.add_all(
        [
            BusyBlock(
                user_id=user1.id,
                weekday=0,
                start_time=time(0, 0),
                end_time=time(4, 0),
            ),
            BusyBlock(
                user_id=user2.id,
                weekday=0,
                start_time=time(20, 0),
                end_time=time(23, 59, 59),
            ),
        ]
    )
    db_session.commit()

    # Date: 2026-11-16 is Monday
    slots = get_group_availability_slots(
        db_session,
        group_id=group.id,
        current_user_id=user1.id,
        target_date=date(2026, 11, 16),
        min_duration_minutes=60,
    )

    # Common free window between 04:00 and 20:00 (16 hours = 960 min)
    assert len(slots) == 1
    assert slots[0].start_time == time(4, 0)
    assert slots[0].end_time == time(20, 0)
    assert slots[0].duration_minutes == 960
    assert slots[0].free_members_count == 2


def test_slots_min_free_members_parameter(
    client: TestClient, db_session: Session
) -> None:
    """Specifying min_free_members finds slots where a quorum is available."""
    u1, t1 = register_and_login(client, "quorum1@example.com")
    u2, t2 = register_and_login(client, "quorum2@example.com")
    u3, t3 = register_and_login(client, "quorum3@example.com")

    group = client.post(
        GROUPS_URL, json={"name": "Quorum Group"}, headers=auth_header(t1)
    ).json()
    client.post(
        "/api/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(t2),
    )
    client.post(
        "/api/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth_header(t3),
    )

    # Friday (weekday 4):
    # u1 is busy 10:00 - 14:00
    # u2 and u3 are free all day Friday
    db_session.add(
        BusyBlock(
            user_id=u1["id"],
            weekday=4,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
    )
    db_session.commit()

    # Query with min_free_members=3 (all must be free) on Friday 2026-11-20
    all_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-20&min_free_members=3&min_duration=60",
        headers=auth_header(t1),
    )
    assert all_res.status_code == 200
    all_slots = all_res.json()
    # 00:00 to 10:00 and 14:00 to 23:59:59
    assert len(all_slots) == 2

    # Query with min_free_members=2 (at least 2 free) -> covers the whole day because u2 and u3 are free all day!
    quorum_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-20&min_free_members=2&min_duration=60",
        headers=auth_header(t1),
    )
    assert quorum_res.status_code == 200
    quorum_slots = quorum_res.json()
    assert len(quorum_slots) == 1
    assert quorum_slots[0]["start_time"] == "00:00:00"
    assert quorum_slots[0]["end_time"] == "23:59:59"
    assert quorum_slots[0]["free_members_count"] == 2
    assert set(quorum_slots[0]["free_member_ids"]) == {u2["id"], u3["id"]}

    # Query with min_free_members > total members (e.g. 4) -> returns empty list []
    impossible_res = client.get(
        f"{GROUPS_URL}/{group['id']}/availability/slots?date=2026-11-20&min_free_members=4",
        headers=auth_header(t1),
    )
    assert impossible_res.status_code == 200
    assert impossible_res.json() == []


def test_merge_intervals_helper() -> None:
    """Helper unit test for interval merging."""
    assert merge_intervals([]) == []
    assert merge_intervals([(10, 20)]) == [(10, 20)]
    assert merge_intervals([(10, 20), (20, 30)]) == [(10, 30)]
    assert merge_intervals([(10, 25), (15, 30), (35, 40)]) == [(10, 30), (35, 40)]
