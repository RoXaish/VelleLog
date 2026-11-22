from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry
from app.models.user import User

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
JOURNAL_URL = "/api/journal-entries"
TAGS_URL = "/api/tags"
DASHBOARD_URL = "/api/dashboard"
RAW_PASSWORD = "s3cure-passphrase"


def register_and_login(
    client: TestClient,
    email: str = "dashboard@example.com",
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


def create_entry(
    client: TestClient,
    token: str,
    title: str,
    content: str,
    mood: str | None = None,
    tag_ids: list[int] | None = None,
) -> dict:
    payload: dict = {"title": title, "content": content}
    if mood is not None:
        payload["mood"] = mood
    if tag_ids is not None:
        payload["tag_ids"] = tag_ids

    response = client.post(
        JOURNAL_URL,
        json=payload,
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def add_entry_at(
    db: Session,
    user_id: int,
    title: str,
    created_at: datetime,
) -> JournalEntry:
    entry = JournalEntry(
        user_id=user_id,
        title=title,
        content=f"Body for {title}",
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def user_id_for(db: Session, email: str) -> int:
    return db.execute(select(User.id).where(User.email == email)).scalar_one()


def test_dashboard_requires_authentication(
    client: TestClient, db_session: Session
) -> None:
    client.cookies.clear()
    response = client.get(DASHBOARD_URL)
    assert response.status_code == 401


def test_empty_dashboard_for_new_user(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "empty_dashboard@example.com")

    response = client.get(DASHBOARD_URL, headers=auth_header(token))

    assert response.status_code == 200
    assert response.json() == {
        "total_entries": 0,
        "entries_this_week": 0,
        "current_streak": 0,
        "recent_entries": [],
    }


def test_dashboard_counts_recent_entries_and_streak(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "filled_dashboard@example.com")
    tag = client.post(
        TAGS_URL,
        json={"name": "Reflection"},
        headers=auth_header(token),
    ).json()

    created = []
    for index in range(6):
        created.append(
            create_entry(
                client,
                token,
                f"Entry {index}",
                f"Body {index}",
                mood="calm" if index % 2 == 0 else "happy",
                tag_ids=[tag["id"]] if index == 5 else [],
            )
        )

    response = client.get(DASHBOARD_URL, headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_entries"] == 6
    assert body["entries_this_week"] == 6
    assert body["current_streak"] == 1
    assert len(body["recent_entries"]) == 5
    assert [entry["id"] for entry in body["recent_entries"]] == [
        entry["id"] for entry in reversed(created[1:])
    ]
    assert body["recent_entries"][0]["mood"] == "happy"
    assert body["recent_entries"][0]["tags"] == [
        {"id": tag["id"], "name": "Reflection"}
    ]
    assert body["recent_entries"][1]["tags"] == []
    tagged = next(
        entry
        for entry in body["recent_entries"]
        if entry["id"] == created[5]["id"]
    )
    assert tagged["mood"] == "happy"
    assert tagged["tags"] == [{"id": tag["id"], "name": "Reflection"}]


def test_dashboard_streak_uses_consecutive_days(
    client: TestClient, db_session: Session
) -> None:
    email = "streak_dashboard@example.com"
    _, token = register_and_login(client, email)
    user_id = user_id_for(db_session, email)

    today = datetime.now(timezone.utc).date()
    for offset in (0, 1, 2):
        day = today - timedelta(days=offset)
        add_entry_at(
            db_session,
            user_id,
            f"Day -{offset}",
            datetime.combine(day, time(hour=12), tzinfo=timezone.utc),
        )
    gap_day = today - timedelta(days=4)
    add_entry_at(
        db_session,
        user_id,
        "Gap day",
        datetime.combine(gap_day, time(hour=12), tzinfo=timezone.utc),
    )

    response = client.get(DASHBOARD_URL, headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["current_streak"] == 3
    assert response.json()["total_entries"] == 4


def test_dashboard_streak_can_end_yesterday(
    client: TestClient, db_session: Session
) -> None:
    email = "yesterday_streak@example.com"
    _, token = register_and_login(client, email)
    user_id = user_id_for(db_session, email)

    today = datetime.now(timezone.utc).date()
    for offset in (1, 2):
        day = today - timedelta(days=offset)
        add_entry_at(
            db_session,
            user_id,
            f"Day -{offset}",
            datetime.combine(day, time(hour=12), tzinfo=timezone.utc),
        )

    body = client.get(DASHBOARD_URL, headers=auth_header(token)).json()

    assert body["current_streak"] == 2


def test_dashboard_streak_is_zero_after_a_full_gap_day(
    client: TestClient, db_session: Session
) -> None:
    email = "broken_streak@example.com"
    _, token = register_and_login(client, email)
    user_id = user_id_for(db_session, email)

    today = datetime.now(timezone.utc).date()
    old_day = today - timedelta(days=3)
    add_entry_at(
        db_session,
        user_id,
        "Old entry",
        datetime.combine(old_day, time(hour=12), tzinfo=timezone.utc),
    )

    body = client.get(DASHBOARD_URL, headers=auth_header(token)).json()

    assert body["current_streak"] == 0


def test_dashboard_entries_this_week_uses_monday_boundary(
    client: TestClient, db_session: Session
) -> None:
    email = "week_dashboard@example.com"
    _, token = register_and_login(client, email)
    user_id = user_id_for(db_session, email)

    today = datetime.now(timezone.utc).date()
    week_start = datetime.combine(
        today - timedelta(days=today.weekday()),
        time.min,
        tzinfo=timezone.utc,
    )
    add_entry_at(
        db_session,
        user_id,
        "This week",
        week_start + timedelta(hours=1),
    )
    add_entry_at(
        db_session,
        user_id,
        "Last week",
        week_start - timedelta(hours=1),
    )

    body = client.get(DASHBOARD_URL, headers=auth_header(token)).json()

    assert body["total_entries"] == 2
    assert body["entries_this_week"] == 1


def test_dashboard_is_isolated_per_user(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "dashboard_alice@example.com")
    _, bob_token = register_and_login(client, "dashboard_bob@example.com")
    create_entry(client, alice_token, "Alice only", "Private to Alice.")

    alice = client.get(DASHBOARD_URL, headers=auth_header(alice_token)).json()
    bob = client.get(DASHBOARD_URL, headers=auth_header(bob_token)).json()

    assert alice["total_entries"] == 1
    assert [entry["title"] for entry in alice["recent_entries"]] == ["Alice only"]
    assert bob["total_entries"] == 0
    assert bob["recent_entries"] == []
