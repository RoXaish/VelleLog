import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
JOURNAL_URL = "/api/journal-entries"
TAGS_URL = "/api/tags"
RAW_PASSWORD = "s3cure-passphrase"

MOODS = [
    "happy",
    "calm",
    "excited",
    "grateful",
    "neutral",
    "sad",
    "anxious",
    "stressed",
]


def register_and_login(
    client: TestClient,
    email: str = "journal_tags@example.com",
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


def create_tag(client: TestClient, token: str, name: str) -> dict:
    response = client.post(
        TAGS_URL,
        json={"name": name},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


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


@pytest.mark.parametrize("mood", MOODS)
def test_create_entry_accepts_supported_moods(
    client: TestClient,
    db_session: Session,
    mood: str,
) -> None:
    _, token = register_and_login(client, f"mood_{mood}@example.com")

    entry = create_entry(
        client,
        token,
        f"A {mood} day",
        "A short note about the day.",
        mood=mood,
    )

    assert entry["mood"] == mood


def test_create_entry_with_tags_and_mood(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "create_tagged@example.com")
    work = create_tag(client, token, "Work")
    calm = create_tag(client, token, "Calm")

    entry = create_entry(
        client,
        token,
        "Focused morning",
        "Deep work before the world woke up.",
        mood="happy",
        tag_ids=[work["id"], calm["id"], work["id"]],
    )

    assert entry["mood"] == "happy"
    assert [tag["name"] for tag in entry["tags"]] == ["Calm", "Work"]

    fetched = client.get(
        f"{JOURNAL_URL}/{entry['id']}",
        headers=auth_header(token),
    ).json()
    assert fetched["mood"] == "happy"
    assert {tag["name"] for tag in fetched["tags"]} == {"Calm", "Work"}


@pytest.mark.parametrize("mood", ["ecstatic", "tired", ""])
def test_create_entry_rejects_unsupported_moods(
    client: TestClient,
    db_session: Session,
    mood: str,
) -> None:
    _, token = register_and_login(client, f"bad_mood_{mood or 'blank'}@example.com")

    response = client.post(
        JOURNAL_URL,
        json={
            "title": "Bad mood",
            "content": "This should not save.",
            "mood": mood,
        },
        headers=auth_header(token),
    )

    assert response.status_code == 422


def test_update_mood_and_tags_and_remove_them(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "update_tags@example.com")
    work = create_tag(client, token, "Work")
    calm = create_tag(client, token, "Calm")
    entry = create_entry(
        client,
        token,
        "Changing feelings",
        "The day shifted as it went.",
        mood="happy",
        tag_ids=[work["id"]],
    )

    updated = client.patch(
        f"{JOURNAL_URL}/{entry['id']}",
        json={"mood": "calm", "tag_ids": [calm["id"]]},
        headers=auth_header(token),
    )
    assert updated.status_code == 200
    assert updated.json()["mood"] == "calm"
    assert [tag["name"] for tag in updated.json()["tags"]] == ["Calm"]

    removed_mood = client.patch(
        f"{JOURNAL_URL}/{entry['id']}",
        json={"mood": None},
        headers=auth_header(token),
    )
    assert removed_mood.status_code == 200
    assert removed_mood.json()["mood"] is None
    assert [tag["name"] for tag in removed_mood.json()["tags"]] == ["Calm"]

    cleared_tags = client.patch(
        f"{JOURNAL_URL}/{entry['id']}",
        json={"tag_ids": []},
        headers=auth_header(token),
    )
    assert cleared_tags.status_code == 200
    assert cleared_tags.json()["tags"] == []
    assert cleared_tags.json()["mood"] is None


def test_update_rejects_invalid_mood_tags_and_null_fields(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "update_validation_alice@example.com")
    _, bob_token = register_and_login(client, "update_validation_bob@example.com")
    bob_tag = create_tag(client, bob_token, "Bob only")
    entry = create_entry(
        client,
        alice_token,
        "Valid entry",
        "Valid body.",
    )

    invalid_requests = [
        {"mood": "ecstatic"},
        {"tag_ids": [bob_tag["id"]]},
        {"tag_ids": [999999]},
        {"tag_ids": None},
        {"title": None},
        {"content": None},
        {},
    ]

    for payload in invalid_requests:
        response = client.patch(
            f"{JOURNAL_URL}/{entry['id']}",
            json=payload,
            headers=auth_header(alice_token),
        )
        assert response.status_code in {404, 422}

    still_valid = client.get(
        f"{JOURNAL_URL}/{entry['id']}",
        headers=auth_header(alice_token),
    ).json()
    assert still_valid["title"] == "Valid entry"
    assert still_valid["content"] == "Valid body."
    assert still_valid["tags"] == []
    assert still_valid["mood"] is None


def test_create_rejects_another_users_tag(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "create_tag_alice@example.com")
    _, bob_token = register_and_login(client, "create_tag_bob@example.com")
    bob_tag = create_tag(client, bob_token, "Bob only")

    response = client.post(
        JOURNAL_URL,
        json={
            "title": "Not allowed",
            "content": "This tag belongs to someone else.",
            "tag_ids": [bob_tag["id"]],
        },
        headers=auth_header(alice_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found"


def test_create_rejects_too_many_tags(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "too_many_tags@example.com")

    response = client.post(
        JOURNAL_URL,
        json={
            "title": "Too many tags",
            "content": "This payload has too many tag ids.",
            "tag_ids": list(range(1, 22)),
        },
        headers=auth_header(token),
    )

    assert response.status_code == 422


def test_list_filters_by_tag_and_mood(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "filter_tags@example.com")
    work = create_tag(client, token, "Work")
    calm = create_tag(client, token, "Calm")
    personal = create_tag(client, token, "Personal")

    focused = create_entry(
        client,
        token,
        "Focused morning",
        "Deep work before the world woke up.",
        mood="happy",
        tag_ids=[work["id"]],
    )
    evening = create_entry(
        client,
        token,
        "Soft evening",
        "A quiet close to the day.",
        mood="calm",
        tag_ids=[calm["id"], personal["id"]],
    )
    rainy = create_entry(
        client,
        token,
        "Rainy day",
        "The rain stayed against the window.",
        mood="sad",
        tag_ids=[work["id"], calm["id"]],
    )

    work_only = client.get(
        JOURNAL_URL,
        params=[("tag_ids", work["id"])],
        headers=auth_header(token),
    ).json()
    assert [entry["id"] for entry in work_only["items"]] == [
        rainy["id"],
        focused["id"],
    ]

    work_and_calm = client.get(
        JOURNAL_URL,
        params=[("tag_ids", work["id"]), ("tag_ids", calm["id"])],
        headers=auth_header(token),
    ).json()
    assert [entry["id"] for entry in work_and_calm["items"]] == [rainy["id"]]

    calm_mood = client.get(
        f"{JOURNAL_URL}?mood=calm",
        headers=auth_header(token),
    ).json()
    assert [entry["id"] for entry in calm_mood["items"]] == [evening["id"]]

    happy_and_work = client.get(
        JOURNAL_URL,
        params=[("mood", "happy"), ("tag_ids", work["id"])],
        headers=auth_header(token),
    ).json()
    assert [entry["id"] for entry in happy_and_work["items"]] == [focused["id"]]

    searched = client.get(
        JOURNAL_URL,
        params=[
            ("search", "evening"),
            ("tag_ids", calm["id"]),
        ],
        headers=auth_header(token),
    ).json()
    assert [entry["id"] for entry in searched["items"]] == [evening["id"]]

    no_match = client.get(
        JOURNAL_URL,
        params=[
            ("mood", "anxious"),
            ("tag_ids", personal["id"]),
        ],
        headers=auth_header(token),
    ).json()
    assert no_match["items"] == []
    assert no_match["total"] == 0


def test_list_rejects_filtering_by_another_users_tag(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "filter_alice@example.com")
    _, bob_token = register_and_login(client, "filter_bob@example.com")
    bob_tag = create_tag(client, bob_token, "Bob only")

    response = client.get(
        JOURNAL_URL,
        params=[("tag_ids", bob_tag["id"])],
        headers=auth_header(alice_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found"


def test_list_includes_tags_and_mood(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "list_tags@example.com")
    tag = create_tag(client, token, "Reflection")
    create_entry(
        client,
        token,
        "A reflective day",
        "Looking back with care.",
        mood="grateful",
        tag_ids=[tag["id"]],
    )

    response = client.get(JOURNAL_URL, headers=auth_header(token))

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["mood"] == "grateful"
    assert item["tags"] == [{"id": tag["id"], "name": "Reflection"}]
