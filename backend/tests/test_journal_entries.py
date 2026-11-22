import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
JOURNAL_URL = "/api/journal-entries"
RAW_PASSWORD = "s3cure-passphrase"
CSRF_COOKIE = "velle_csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def register_and_login(
    client: TestClient,
    email: str = "journal@example.com",
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
    title: str = "A quiet morning",
    content: str = "The light came through the window before the city woke up.",
) -> dict:
    response = client.post(
        JOURNAL_URL,
        json={"title": title, "content": content},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def test_journal_endpoints_require_authentication(
    client: TestClient, db_session: Session
) -> None:
    client.cookies.clear()

    responses = [
        client.post(
            JOURNAL_URL,
            json={"title": "Private", "content": "Private thoughts"},
        ),
        client.get(JOURNAL_URL),
        client.get(f"{JOURNAL_URL}/1"),
        client.patch(f"{JOURNAL_URL}/1", json={"title": "Changed"}),
        client.delete(f"{JOURNAL_URL}/1"),
    ]

    for response in responses:
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"


def test_create_entry_success(client: TestClient, db_session: Session) -> None:
    user, token = register_and_login(client)

    response = client.post(
        JOURNAL_URL,
        json={
            "title": "  A quiet morning  ",
            "content": "  The light came through the window.  ",
        },
        headers=auth_header(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == user["id"]
    assert body["title"] == "A quiet morning"
    assert body["content"] == "The light came through the window."
    assert body["created_at"]
    assert body["updated_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "Only a title"},
        {"content": "Only content"},
        {"title": "", "content": "Content"},
        {"title": "   ", "content": "Content"},
        {"title": "Title", "content": ""},
        {"title": "Title", "content": "   "},
        {"title": "x" * 201, "content": "Content"},
        {"title": "Title", "content": "x" * 50001},
    ],
)
def test_create_entry_validation(
    client: TestClient,
    db_session: Session,
    payload: dict[str, str],
) -> None:
    _, token = register_and_login(client, "validation@example.com")

    response = client.post(
        JOURNAL_URL,
        json=payload,
        headers=auth_header(token),
    )

    assert response.status_code == 422


def test_list_entries_is_newest_first_and_user_scoped(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "alice_journal@example.com")
    _, bob_token = register_and_login(client, "bob_journal@example.com")

    first = create_entry(client, alice_token, "First", "First entry body")
    second = create_entry(client, alice_token, "Second", "Second entry body")
    third = create_entry(client, alice_token, "Third", "Third entry body")
    bob_entry = create_entry(client, bob_token, "Bob only", "Bob's private body")

    response = client.get(JOURNAL_URL, headers=auth_header(alice_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]
    assert all(item["user_id"] != bob_entry["user_id"] for item in body["items"])
    assert "Bob only" not in response.text
    assert "Bob's private body" not in response.text


def test_pagination_metadata_and_ordering(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "pagination@example.com")
    created = [
        create_entry(client, token, f"Entry {index}", f"Body {index}")
        for index in range(5)
    ]

    first_page = client.get(
        f"{JOURNAL_URL}?page=1&page_size=2",
        headers=auth_header(token),
    ).json()

    assert first_page["total"] == 5
    assert first_page["page"] == 1
    assert first_page["page_size"] == 2
    assert first_page["total_pages"] == 3
    assert first_page["has_previous"] is False
    assert first_page["has_next"] is True
    assert [item["id"] for item in first_page["items"]] == [
        created[4]["id"],
        created[3]["id"],
    ]

    middle_page = client.get(
        f"{JOURNAL_URL}?page=2&page_size=2",
        headers=auth_header(token),
    ).json()

    assert middle_page["has_previous"] is True
    assert middle_page["has_next"] is True
    assert [item["id"] for item in middle_page["items"]] == [
        created[2]["id"],
        created[1]["id"],
    ]

    last_page = client.get(
        f"{JOURNAL_URL}?page=3&page_size=2",
        headers=auth_header(token),
    ).json()

    assert last_page["has_previous"] is True
    assert last_page["has_next"] is False
    assert [item["id"] for item in last_page["items"]] == [created[0]["id"]]


@pytest.mark.parametrize(
    "query",
    ["page=0", "page_size=0", "page_size=101"],
)
def test_pagination_rejects_invalid_parameters(
    client: TestClient, db_session: Session, query: str
) -> None:
    _, token = register_and_login(client, "page_validation@example.com")

    response = client.get(
        f"{JOURNAL_URL}?{query}",
        headers=auth_header(token),
    )

    assert response.status_code == 422


def test_search_matches_title_and_content_case_insensitively(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "search@example.com")
    morning = create_entry(
        client,
        token,
        "Morning Pages",
        "Coffee, quiet, and a blank page.",
    )
    rain = create_entry(
        client,
        token,
        "Afternoon",
        "The RAIN stayed against the window for hours.",
    )
    create_entry(client, token, "Evening", "A completely unrelated note.")

    title_response = client.get(
        f"{JOURNAL_URL}?search=morning",
        headers=auth_header(token),
    )
    assert title_response.status_code == 200
    assert [item["id"] for item in title_response.json()["items"]] == [morning["id"]]

    content_response = client.get(
        f"{JOURNAL_URL}?search=rain",
        headers=auth_header(token),
    )
    assert content_response.status_code == 200
    assert [item["id"] for item in content_response.json()["items"]] == [rain["id"]]


def test_search_treats_like_wildcards_literally(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "wildcard@example.com")
    create_entry(client, token, "100% present", "A literal percent sign.")
    create_entry(client, token, "Underscore", "A normal body.")

    response = client.get(
        f"{JOURNAL_URL}?search=%25",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["100% present"]


def test_get_entry_owns_only_own_entries(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "get_alice@example.com")
    _, bob_token = register_and_login(client, "get_bob@example.com")
    alice_entry = create_entry(client, alice_token, "Alice", "Alice body")

    own_response = client.get(
        f"{JOURNAL_URL}/{alice_entry['id']}",
        headers=auth_header(alice_token),
    )
    assert own_response.status_code == 200
    assert own_response.json()["title"] == "Alice"

    other_response = client.get(
        f"{JOURNAL_URL}/{alice_entry['id']}",
        headers=auth_header(bob_token),
    )
    assert other_response.status_code == 404
    assert other_response.json()["detail"] == "Journal entry not found"

    missing_response = client.get(
        f"{JOURNAL_URL}/999999",
        headers=auth_header(alice_token),
    )
    assert missing_response.status_code == 404


def test_update_entry_and_reject_invalid_changes(
    client: TestClient, db_session: Session
) -> None:
    _, token = register_and_login(client, "update@example.com")
    entry = create_entry(client, token, "Old title", "Old body")

    title_update = client.patch(
        f"{JOURNAL_URL}/{entry['id']}",
        json={"title": "  New title  "},
        headers=auth_header(token),
    )
    assert title_update.status_code == 200
    assert title_update.json()["title"] == "New title"
    assert title_update.json()["content"] == "Old body"

    content_update = client.patch(
        f"{JOURNAL_URL}/{entry['id']}",
        json={"content": "  New body  "},
        headers=auth_header(token),
    )
    assert content_update.status_code == 200
    assert content_update.json()["title"] == "New title"
    assert content_update.json()["content"] == "New body"

    for payload in [{}, {"title": None}, {"title": "   "}, {"content": "   "}]:
        response = client.patch(
            f"{JOURNAL_URL}/{entry['id']}",
            json=payload,
            headers=auth_header(token),
        )
        assert response.status_code == 422


def test_update_cannot_modify_another_users_entry(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "update_alice@example.com")
    _, bob_token = register_and_login(client, "update_bob@example.com")
    entry = create_entry(client, alice_token, "Alice title", "Alice body")

    response = client.patch(
        f"{JOURNAL_URL}/{entry['id']}",
        json={"title": "Hijacked"},
        headers=auth_header(bob_token),
    )

    assert response.status_code == 404
    still_alice = client.get(
        f"{JOURNAL_URL}/{entry['id']}",
        headers=auth_header(alice_token),
    ).json()
    assert still_alice["title"] == "Alice title"


def test_delete_entry_and_reject_cross_user_delete(
    client: TestClient, db_session: Session
) -> None:
    _, alice_token = register_and_login(client, "delete_alice@example.com")
    _, bob_token = register_and_login(client, "delete_bob@example.com")
    entry = create_entry(client, alice_token, "To delete", "Temporary body")

    forbidden = client.delete(
        f"{JOURNAL_URL}/{entry['id']}",
        headers=auth_header(bob_token),
    )
    assert forbidden.status_code == 404
    assert (
        client.get(
            f"{JOURNAL_URL}/{entry['id']}",
            headers=auth_header(alice_token),
        ).status_code
        == 200
    )

    deleted = client.delete(
        f"{JOURNAL_URL}/{entry['id']}",
        headers=auth_header(alice_token),
    )
    assert deleted.status_code == 204
    assert (
        client.get(
            f"{JOURNAL_URL}/{entry['id']}",
            headers=auth_header(alice_token),
        ).status_code
        == 404
    )


def test_cookie_mutations_require_csrf(
    client: TestClient, db_session: Session
) -> None:
    register_and_login(client, "cookie_journal@example.com")
    payload = {"title": "Cookie entry", "content": "Written from a browser."}

    missing = client.post(JOURNAL_URL, json=payload)
    assert missing.status_code == 403

    csrf_token = client.cookies.get(CSRF_COOKIE)
    assert csrf_token
    created = client.post(
        JOURNAL_URL,
        json=payload,
        headers={CSRF_HEADER: csrf_token},
    )
    assert created.status_code == 201

    entry_id = created.json()["id"]
    updated = client.patch(
        f"{JOURNAL_URL}/{entry_id}",
        json={"title": "Cookie entry updated"},
        headers={CSRF_HEADER: csrf_token},
    )
    assert updated.status_code == 200

    deleted = client.delete(
        f"{JOURNAL_URL}/{entry_id}",
        headers={CSRF_HEADER: csrf_token},
    )
    assert deleted.status_code == 204
