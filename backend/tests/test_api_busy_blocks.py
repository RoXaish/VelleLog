import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

BUSY_BLOCKS_URL = "/api/busy-blocks"
COPY_DAY_URL = "/api/busy-blocks/copy-day"
REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
RAW_PASSWORD = "s3cure-passphrase"


def register_and_login(
    client: TestClient,
    email: str = "busy_tester@example.com",
    password: str = RAW_PASSWORD,
) -> tuple[dict, str]:
    """Helper to register and login a user, returning user data and bearer token."""
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
# 1. Authentication (401 Unauthorized)
# ==============================================================================


@pytest.mark.parametrize(
    "method,url,payload",
    [
        ("post", BUSY_BLOCKS_URL, {"weekday": 0, "start_time": "09:00:00", "end_time": "10:00:00"}),
        ("get", BUSY_BLOCKS_URL, None),
        ("post", COPY_DAY_URL, {"source_weekday": 0, "target_weekday": 1}),
        ("patch", f"{BUSY_BLOCKS_URL}/1", {"private_label": "New"}),
        ("delete", f"{BUSY_BLOCKS_URL}/1", None),
    ],
)
def test_busy_blocks_require_authentication(
    client: TestClient, db_session: Session, method: str, url: str, payload: dict | None
) -> None:
    """All busy block endpoints reject unauthenticated requests with 401."""
    client.cookies.clear()
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(client, method)(url, **kwargs)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


# ==============================================================================
# 2. Validation (422 Unprocessable Entity)
# ==============================================================================


@pytest.mark.parametrize("invalid_weekday", [-1, 7, 100])
def test_create_rejects_invalid_weekday(
    client: TestClient, db_session: Session, invalid_weekday: int
) -> None:
    """Weekday outside 0-6 returns 422."""
    _, token = register_and_login(client, "val_wk@example.com")
    response = client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": invalid_weekday, "start_time": "09:00:00", "end_time": "10:00:00"},
        headers=auth_header(token),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "start,end",
    [
        ("10:00:00", "10:00:00"),  # Equal times
        ("11:00:00", "10:00:00"),  # Inverted times
    ],
)
def test_create_rejects_invalid_time_range(
    client: TestClient, db_session: Session, start: str, end: str
) -> None:
    """start_time >= end_time returns 422."""
    _, token = register_and_login(client, "val_time@example.com")
    response = client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 1, "start_time": start, "end_time": end},
        headers=auth_header(token),
    )
    assert response.status_code == 422


def test_copy_day_rejects_same_source_and_target(
    client: TestClient, db_session: Session
) -> None:
    """source_weekday equal to target_weekday returns 422."""
    _, token = register_and_login(client, "val_copy@example.com")
    response = client.post(
        COPY_DAY_URL,
        json={"source_weekday": 2, "target_weekday": 2},
        headers=auth_header(token),
    )
    assert response.status_code == 422


def test_invalid_block_id_type_returns_422(
    client: TestClient, db_session: Session
) -> None:
    """Non-integer block_id in URL returns 422."""
    _, token = register_and_login(client, "id_val_bb@example.com")
    assert client.patch(f"{BUSY_BLOCKS_URL}/not-an-int", json={}, headers=auth_header(token)).status_code == 422
    assert client.delete(f"{BUSY_BLOCKS_URL}/not-an-int", headers=auth_header(token)).status_code == 422


# ==============================================================================
# 3. CRUD Operations
# ==============================================================================


def test_create_and_get_busy_blocks(client: TestClient, db_session: Session) -> None:
    """Create busy blocks and retrieve them ordered by weekday and start_time."""
    user, token = register_and_login(client, "crud_user@example.com")

    # Initial list is empty
    empty_res = client.get(BUSY_BLOCKS_URL, headers=auth_header(token))
    assert empty_res.status_code == 200
    assert empty_res.json() == []

    # Create block on Tuesday 14:00 - 15:30
    b1_res = client.post(
        BUSY_BLOCKS_URL,
        json={
            "weekday": 1,
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "private_label": "Project Meeting",
        },
        headers=auth_header(token),
    )
    assert b1_res.status_code == 201
    b1 = b1_res.json()
    assert b1["id"] is not None
    assert b1["user_id"] == user["id"]
    assert b1["weekday"] == 1
    assert b1["start_time"] == "14:00:00"
    assert b1["end_time"] == "15:30:00"
    assert b1["private_label"] == "Project Meeting"
    assert "created_at" in b1
    assert "updated_at" in b1

    # Create block on Monday 09:00 - 10:00 (without private label)
    b2_res = client.post(
        BUSY_BLOCKS_URL,
        json={
            "weekday": 0,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
        headers=auth_header(token),
    )
    assert b2_res.status_code == 201
    b2 = b2_res.json()
    assert b2["private_label"] is None

    # Retrieve all blocks -> ordered by weekday asc, start_time asc
    list_res = client.get(BUSY_BLOCKS_URL, headers=auth_header(token))
    assert list_res.status_code == 200
    blocks = list_res.json()
    assert len(blocks) == 2
    assert blocks[0]["id"] == b2["id"]  # Monday block first
    assert blocks[1]["id"] == b1["id"]  # Tuesday block second


def test_update_busy_block(client: TestClient, db_session: Session) -> None:
    """PATCH updates block attributes and validates resulting time ranges."""
    _, token = register_and_login(client, "update_user@example.com")

    # Create initial block: Mon 09:00 - 11:00
    create_res = client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 0, "start_time": "09:00:00", "end_time": "11:00:00", "private_label": "Work"},
        headers=auth_header(token),
    )
    block_id = create_res.json()["id"]

    # Partial update: change private_label and end_time
    patch_res = client.patch(
        f"{BUSY_BLOCKS_URL}/{block_id}",
        json={"end_time": "10:30:00", "private_label": "Deep Work"},
        headers=auth_header(token),
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["end_time"] == "10:30:00"
    assert updated["start_time"] == "09:00:00"
    assert updated["private_label"] == "Deep Work"

    # Attempt invalid time range update (new start_time later than current end_time 10:30:00)
    bad_time_res = client.patch(
        f"{BUSY_BLOCKS_URL}/{block_id}",
        json={"start_time": "11:00:00"},
        headers=auth_header(token),
    )
    assert bad_time_res.status_code == 422

    # Attempt invalid time range update (new end_time earlier than current start_time 09:00:00)
    bad_end_res = client.patch(
        f"{BUSY_BLOCKS_URL}/{block_id}",
        json={"end_time": "08:30:00"},
        headers=auth_header(token),
    )
    assert bad_end_res.status_code == 422

    # Attempt updating non-existent block -> 404
    not_found_res = client.patch(
        f"{BUSY_BLOCKS_URL}/999999",
        json={"private_label": "Ghost"},
        headers=auth_header(token),
    )
    assert not_found_res.status_code == 404

    # Attempt invalid weekday update -> 422
    bad_wk_res = client.patch(
        f"{BUSY_BLOCKS_URL}/{block_id}",
        json={"weekday": 10},
        headers=auth_header(token),
    )
    assert bad_wk_res.status_code == 422


def test_delete_busy_block(client: TestClient, db_session: Session) -> None:
    """DELETE removes the block; subsequent retrieval does not include it."""
    _, token = register_and_login(client, "delete_user@example.com")

    create_res = client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 4, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=auth_header(token),
    )
    block_id = create_res.json()["id"]

    # Delete block
    del_res = client.delete(f"{BUSY_BLOCKS_URL}/{block_id}", headers=auth_header(token))
    assert del_res.status_code == 204

    # Verify deleted from list
    list_res = client.get(BUSY_BLOCKS_URL, headers=auth_header(token))
    assert len(list_res.json()) == 0

    # Delete non-existent block returns 404
    del_nonexistent = client.delete(f"{BUSY_BLOCKS_URL}/{block_id}", headers=auth_header(token))
    assert del_nonexistent.status_code == 404


# ==============================================================================
# 4. Ownership & Access Control
# ==============================================================================


def test_users_cannot_access_or_modify_other_users_blocks(
    client: TestClient, db_session: Session
) -> None:
    """Users cannot view, update, or delete blocks belonging to other users."""
    _, token_alice = register_and_login(client, "alice_bb@example.com")
    _, token_bob = register_and_login(client, "bob_bb@example.com")

    # Alice creates a block
    alice_block = client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 2, "start_time": "10:00:00", "end_time": "12:00:00", "private_label": "Alice Secret"},
        headers=auth_header(token_alice),
    ).json()

    # Bob's list does not contain Alice's block
    bob_list = client.get(BUSY_BLOCKS_URL, headers=auth_header(token_bob)).json()
    assert len(bob_list) == 0

    # Bob tries to patch Alice's block -> 403 Forbidden
    patch_attempt = client.patch(
        f"{BUSY_BLOCKS_URL}/{alice_block['id']}",
        json={"private_label": "Hacked"},
        headers=auth_header(token_bob),
    )
    assert patch_attempt.status_code == 403
    assert "access denied" in patch_attempt.json()["detail"].lower()

    # Bob tries to delete Alice's block -> 403 Forbidden
    delete_attempt = client.delete(
        f"{BUSY_BLOCKS_URL}/{alice_block['id']}",
        headers=auth_header(token_bob),
    )
    assert delete_attempt.status_code == 403
    assert "access denied" in delete_attempt.json()["detail"].lower()


# ==============================================================================
# 5. Copy-Day Behavior
# ==============================================================================


def test_copy_day_replaces_target_day_and_preserves_labels(
    client: TestClient, db_session: Session
) -> None:
    """Copy-day replaces target day blocks with source day blocks and keeps labels."""
    _, token = register_and_login(client, "copy_day_user@example.com")

    # Monday (weekday 0) has 2 blocks
    client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 0, "start_time": "09:00:00", "end_time": "10:30:00", "private_label": "Morning Standup"},
        headers=auth_header(token),
    )
    client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 0, "start_time": "14:00:00", "end_time": "15:00:00", "private_label": "Gym"},
        headers=auth_header(token),
    )

    # Wednesday (weekday 2) already has an existing obsolete block
    client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 2, "start_time": "11:00:00", "end_time": "12:00:00", "private_label": "Old Meeting"},
        headers=auth_header(token),
    )

    # Copy Monday (0) to Wednesday (2)
    copy_res = client.post(
        COPY_DAY_URL,
        json={"source_weekday": 0, "target_weekday": 2},
        headers=auth_header(token),
    )
    assert copy_res.status_code == 200
    copied = copy_res.json()
    assert len(copied) == 2
    assert [c["weekday"] for c in copied] == [2, 2]
    assert [c["start_time"] for c in copied] == ["09:00:00", "14:00:00"]
    assert [c["end_time"] for c in copied] == ["10:30:00", "15:00:00"]
    assert [c["private_label"] for c in copied] == ["Morning Standup", "Gym"]

    # Verify complete schedule for user
    all_blocks = client.get(BUSY_BLOCKS_URL, headers=auth_header(token)).json()
    # 2 on Monday (0) + 2 on Wednesday (2), old Wednesday block removed -> total 4
    assert len(all_blocks) == 4
    wednesday_blocks = [b for b in all_blocks if b["weekday"] == 2]
    assert len(wednesday_blocks) == 2
    assert all(b["private_label"] != "Old Meeting" for b in wednesday_blocks)


def test_copy_empty_day_clears_target_day(
    client: TestClient, db_session: Session
) -> None:
    """Copying from a weekday with no blocks clears all blocks on the target weekday."""
    _, token = register_and_login(client, "empty_copy_user@example.com")

    # Target day (Thursday 3) has a block
    client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 3, "start_time": "10:00:00", "end_time": "11:00:00"},
        headers=auth_header(token),
    )

    # Sunday (weekday 6) has 0 blocks. Copy Sunday (6) to Thursday (3)
    copy_res = client.post(
        COPY_DAY_URL,
        json={"source_weekday": 6, "target_weekday": 3},
        headers=auth_header(token),
    )
    assert copy_res.status_code == 200
    assert copy_res.json() == []

    # Verify Thursday now has 0 blocks
    all_blocks = client.get(BUSY_BLOCKS_URL, headers=auth_header(token)).json()
    assert len(all_blocks) == 0


def test_busy_blocks_support_cookie_authentication(
    client: TestClient, db_session: Session
) -> None:
    """Busy block endpoints authenticate seamlessly via HttpOnly cookies."""
    client.post(
        REGISTER_URL,
        json={"email": "cookie_bb@example.com", "password": RAW_PASSWORD},
    )
    client.post(
        LOGIN_URL,
        json={"email": "cookie_bb@example.com", "password": RAW_PASSWORD},
    )

    # Create via cookie auth
    create_res = client.post(
        BUSY_BLOCKS_URL,
        json={"weekday": 5, "start_time": "10:00:00", "end_time": "11:00:00", "private_label": "Saturday Yoga"},
    )
    assert create_res.status_code == 201
    block_id = create_res.json()["id"]

    # List via cookie auth
    list_res = client.get(BUSY_BLOCKS_URL)
    assert list_res.status_code == 200
    assert any(b["id"] == block_id for b in list_res.json())
