import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
TAGS_URL = "/api/tags"
JOURNAL_URL = "/api/journal-entries"
RAW_PASSWORD = "s3cure-passphrase"
CSRF_COOKIE = "velle_csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def register_and_login(
    client: TestClient,
    email: str = "tags@example.com",
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


def test_tag_endpoints_require_authentication(
    client: TestClient, db_session: Session
) -> None:
    client.cookies.clear()

    responses = [
        client.get(TAGS_URL),
        client.post(TAGS_URL, json={"name": "Work"}),
        client.patch(f"{TAGS_URL}/1", json={"name": "Life"}),
        client.delete(f"{TAGS_URL}/1"),
    ]

    for response in responses:
        assert response.status_code == 401


def test_create_list_rename_and_delete_tags(
    client: TestClient, db_session: Session
) -> None:
    user, token = register_and_login(client)

    work = create_tag(client, token, "  Work  ")
    personal = create_tag(client, token, "Personal")
    assert work["name"] == "Work"
    assert work["user_id"] == user["id"]
    assert work["entry_count"] == 0

    listed = client.get(TAGS_URL, headers=auth_header(token))
    assert listed.status_code == 200
    assert [tag["name"] for tag in listed.json()] == ["Personal", "Work"]

    renamed = client.patch(
        f"{TAGS_URL}/{personal['id']}",
        json={"name": "Life"},
        headers=auth_header(token),
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Life"

    deleted = client.delete(
        f"{TAGS_URL}/{work['id']}",
        headers=auth_header(token),
    )
    assert deleted.status_code == 204

    remaining = client.get(TAGS_URL, headers=auth_header(token)).json()
    assert [tag["name"] for tag in remaining] == ["Life"]


def test_tag_names_are_unique_per_user_case_insensitively(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "unique_tags@example.com")
    work = create_tag(client, token, "Work")

    duplicate = client.post(
        TAGS_URL,
        json={"name": "work"},
        headers=auth_header(token),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A tag with that name already exists"

    other = create_tag(client, token, "Personal")
    rename_conflict = client.patch(
        f"{TAGS_URL}/{other['id']}",
        json={"name": "WORK"},
        headers=auth_header(token),
    )
    assert rename_conflict.status_code == 409

    unchanged = client.get(TAGS_URL, headers=auth_header(token)).json()
    assert {tag["name"] for tag in unchanged} == {"Work", "Personal"}
    assert any(tag["id"] == work["id"] for tag in unchanged)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 51},
    ],
)
def test_tag_validation(
    client: TestClient,
    db_session: Session,
    payload: dict[str, str],
) -> None:
    _, token = register_and_login(client, "tag_validation@example.com")

    response = client.post(
        TAGS_URL,
        json=payload,
        headers=auth_header(token),
    )

    assert response.status_code == 422


def test_tags_are_isolated_between_users(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "tag_alice@example.com")
    _, bob_token = register_and_login(client, "tag_bob@example.com")

    alice_tag = create_tag(client, alice_token, "Private")
    bob_tag = create_tag(client, bob_token, "Private")

    bob_list = client.get(TAGS_URL, headers=auth_header(bob_token)).json()
    assert [tag["id"] for tag in bob_list] == [bob_tag["id"]]

    assert (
        client.patch(
            f"{TAGS_URL}/{alice_tag['id']}",
            json={"name": "Hijacked"},
            headers=auth_header(bob_token),
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"{TAGS_URL}/{alice_tag['id']}",
            headers=auth_header(bob_token),
        ).status_code
        == 404
    )

    alice_list = client.get(TAGS_URL, headers=auth_header(alice_token)).json()
    assert [tag["name"] for tag in alice_list] == ["Private"]


def test_tag_usage_counts_and_detach_on_delete(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "tag_counts@example.com")
    work = create_tag(client, token, "Work")
    calm = create_tag(client, token, "Calm")

    created = client.post(
        JOURNAL_URL,
        json={
            "title": "A tagged entry",
            "content": "This entry carries two tags.",
            "tag_ids": [work["id"], calm["id"]],
        },
        headers=auth_header(token),
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    listed_tags = client.get(TAGS_URL, headers=auth_header(token)).json()
    assert {tag["name"]: tag["entry_count"] for tag in listed_tags} == {
        "Calm": 1,
        "Work": 1,
    }

    deleted = client.delete(
        f"{TAGS_URL}/{work['id']}",
        headers=auth_header(token),
    )
    assert deleted.status_code == 204

    entry = client.get(
        f"{JOURNAL_URL}/{entry_id}",
        headers=auth_header(token),
    )
    assert entry.status_code == 200
    assert [tag["name"] for tag in entry.json()["tags"]] == ["Calm"]


def test_cookie_tag_mutations_require_csrf(
    client: TestClient, db_session: Session
) -> None:
    register_and_login(client, "tag_csrf@example.com")

    missing = client.post(TAGS_URL, json={"name": "Work"})
    assert missing.status_code == 403

    csrf_token = client.cookies.get(CSRF_COOKIE)
    assert csrf_token
    created = client.post(
        TAGS_URL,
        json={"name": "Work"},
        headers={CSRF_HEADER: csrf_token},
    )
    assert created.status_code == 201

    tag_id = created.json()["id"]
    updated = client.patch(
        f"{TAGS_URL}/{tag_id}",
        json={"name": "Deep work"},
        headers={CSRF_HEADER: csrf_token},
    )
    assert updated.status_code == 200

    deleted = client.delete(
        f"{TAGS_URL}/{tag_id}",
        headers={CSRF_HEADER: csrf_token},
    )
    assert deleted.status_code == 204
