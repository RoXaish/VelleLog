import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.tokens import create_access_token
from app.models.user import User

GROUPS_URL = "/api/groups"
JOIN_URL = "/api/groups/join"
REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
RAW_PASSWORD = "s3cure-passphrase"


def register_and_login(
    client: TestClient,
    email: str = "creator@example.com",
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
# 1. Authentication & Authorization (401 Unauthorized)
# ==============================================================================


@pytest.mark.parametrize(
    "method,url,payload",
    [
        ("post", GROUPS_URL, {"name": "Test Group"}),
        ("get", GROUPS_URL, None),
        ("post", JOIN_URL, {"invite_code": "ABC123XYZ"}),
        ("get", f"{GROUPS_URL}/1", None),
    ],
)
def test_groups_endpoints_require_authentication(
    client: TestClient, db_session: Session, method: str, url: str, payload: dict | None
) -> None:
    """All group endpoints must reject unauthenticated requests with 401."""
    client.cookies.clear()
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(client, method)(url, **kwargs)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


# ==============================================================================
# 2. Validation Errors (422 Unprocessable Entity)
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "   ",
        "a" * 101,
    ],
)
def test_create_group_rejects_invalid_name(
    client: TestClient, db_session: Session, invalid_name: str
) -> None:
    """Empty, whitespace-only, or overly long group names must be rejected with 422."""
    _, token = register_and_login(client, "validator@example.com")
    response = client.post(
        GROUPS_URL,
        json={"name": invalid_name},
        headers=auth_header(token),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "invalid_code",
    [
        "",
        "   ",
        "c" * 33,
    ],
)
def test_join_group_rejects_invalid_invite_code(
    client: TestClient, db_session: Session, invalid_code: str
) -> None:
    """Empty, whitespace-only, or overly long invite codes must be rejected with 422."""
    _, token = register_and_login(client, "join_val@example.com")
    response = client.post(
        JOIN_URL,
        json={"invite_code": invalid_code},
        headers=auth_header(token),
    )
    assert response.status_code == 422


def test_get_group_with_invalid_id_type_returns_422(
    client: TestClient, db_session: Session
) -> None:
    """Passing a non-integer group_id returns 422."""
    _, token = register_and_login(client, "id_val@example.com")
    response = client.get(
        f"{GROUPS_URL}/not-a-number",
        headers=auth_header(token),
    )
    assert response.status_code == 422


# ==============================================================================
# 3. Create Group (POST /api/groups)
# ==============================================================================


def test_create_group_success_and_owner_membership(
    client: TestClient, db_session: Session
) -> None:
    """Creating a group returns 201, sets owner_id, and makes creator an owner member."""
    user, token = register_and_login(client, "alice@example.com")

    response = client.post(
        GROUPS_URL,
        json={"name": "Alice's Circle"},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    group_data = response.json()

    assert group_data["id"] is not None
    assert group_data["name"] == "Alice's Circle"
    assert group_data["owner_id"] == user["id"]
    assert len(group_data["invite_code"]) >= 8
    assert "created_at" in group_data

    # Creator must immediately be able to view details including their owner membership
    detail_res = client.get(
        f"{GROUPS_URL}/{group_data['id']}",
        headers=auth_header(token),
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["members"]) == 1
    assert detail["members"][0]["user_id"] == user["id"]
    assert detail["members"][0]["role"] == "owner"
    assert detail["members"][0]["email"] == "alice@example.com"
    assert detail["members"][0]["user"]["email"] == "alice@example.com"


# ==============================================================================
# 4. List Groups (GET /api/groups)
# ==============================================================================


def test_list_groups_returns_only_user_groups(
    client: TestClient, db_session: Session
) -> None:
    """GET /api/groups returns only groups that the requesting user belongs to."""
    alice, token_alice = register_and_login(client, "alice_list@example.com")
    bob, token_bob = register_and_login(client, "bob_list@example.com")

    # Bob initially has 0 groups
    bob_empty = client.get(GROUPS_URL, headers=auth_header(token_bob))
    assert bob_empty.status_code == 200
    assert bob_empty.json() == []

    # Alice creates two groups
    g1 = client.post(
        GROUPS_URL, json={"name": "Alice Group 1"}, headers=auth_header(token_alice)
    ).json()
    g2 = client.post(
        GROUPS_URL, json={"name": "Alice Group 2"}, headers=auth_header(token_alice)
    ).json()

    # Bob creates one group
    g3 = client.post(
        GROUPS_URL, json={"name": "Bob Group"}, headers=auth_header(token_bob)
    ).json()

    # Alice lists groups -> sees g1 and g2, but NOT g3
    alice_groups = client.get(GROUPS_URL, headers=auth_header(token_alice)).json()
    alice_ids = [g["id"] for g in alice_groups]
    assert g1["id"] in alice_ids
    assert g2["id"] in alice_ids
    assert g3["id"] not in alice_ids

    # Bob joins Alice's Group 1 via invite_code
    join_res = client.post(
        JOIN_URL,
        json={"invite_code": g1["invite_code"]},
        headers=auth_header(token_bob),
    )
    assert join_res.status_code == 200

    # Bob lists groups -> now sees g3 AND g1, but NOT g2
    bob_groups = client.get(GROUPS_URL, headers=auth_header(token_bob)).json()
    bob_ids = [g["id"] for g in bob_groups]
    assert g3["id"] in bob_ids
    assert g1["id"] in bob_ids
    assert g2["id"] not in bob_ids


# ==============================================================================
# 5. Join Group (POST /api/groups/join)
# ==============================================================================


def test_join_group_success_and_conflict_on_duplicate(
    client: TestClient, db_session: Session
) -> None:
    """Joining via invite_code adds member; attempting to join again returns 409."""
    _, token_owner = register_and_login(client, "owner_join@example.com")
    new_user, token_joiner = register_and_login(client, "joiner@example.com")

    # Owner creates group
    group = client.post(
        GROUPS_URL, json={"name": "Joinable Circle"}, headers=auth_header(token_owner)
    ).json()

    # Joiner successfully joins
    join_res = client.post(
        JOIN_URL,
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_joiner),
    )
    assert join_res.status_code == 200
    assert join_res.json()["id"] == group["id"]

    # Verify roster now has 2 members: owner and member
    detail = client.get(
        f"{GROUPS_URL}/{group['id']}",
        headers=auth_header(token_joiner),
    ).json()
    assert len(detail["members"]) == 2
    roles = {m["user_id"]: m["role"] for m in detail["members"]}
    assert roles[new_user["id"]] == "member"

    # Attempt duplicate join by same user -> 409 Conflict
    dup_res = client.post(
        JOIN_URL,
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_joiner),
    )
    assert dup_res.status_code == 409
    assert "already a member" in dup_res.json()["detail"].lower()

    # Owner attempting to join their own group -> 409 Conflict
    owner_dup_res = client.post(
        JOIN_URL,
        json={"invite_code": group["invite_code"]},
        headers=auth_header(token_owner),
    )
    assert owner_dup_res.status_code == 409
    assert "already a member" in owner_dup_res.json()["detail"].lower()


def test_join_group_with_nonexistent_invite_code_returns_404(
    client: TestClient, db_session: Session
) -> None:
    """Non-existent invite code returns 404 Not Found."""
    _, token = register_and_login(client, "ghost_join@example.com")
    response = client.post(
        JOIN_URL,
        json={"invite_code": "DOES_NOT_EXIST_CODE"},
        headers=auth_header(token),
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ==============================================================================
# 6. Group Details & Access Denial (GET /api/groups/{group_id})
# ==============================================================================


def test_get_group_non_member_access_denied_403(
    client: TestClient, db_session: Session
) -> None:
    """Users who are not members of the group receive 403 Forbidden."""
    _, token_owner = register_and_login(client, "secret_owner@example.com")
    _, token_stranger = register_and_login(client, "stranger@example.com")

    # Owner creates private group
    group = client.post(
        GROUPS_URL, json={"name": "Secret Society"}, headers=auth_header(token_owner)
    ).json()

    # Stranger tries to view group details
    response = client.get(
        f"{GROUPS_URL}/{group['id']}",
        headers=auth_header(token_stranger),
    )
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower() or "not a member" in response.json()["detail"].lower()


def test_get_group_nonexistent_id_returns_404(
    client: TestClient, db_session: Session
) -> None:
    """Querying an unknown group_id returns 404 Not Found."""
    _, token = register_and_login(client, "searcher@example.com")
    response = client.get(
        f"{GROUPS_URL}/999999",
        headers=auth_header(token),
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_group_responses_never_expose_private_security_material(
    client: TestClient, db_session: Session
) -> None:
    """Group responses and member lists must never leak password hashes or salts."""
    _, token = register_and_login(client, "security_check@example.com")
    group = client.post(
        GROUPS_URL, json={"name": "Secure Circle"}, headers=auth_header(token)
    ).json()

    detail = client.get(
        f"{GROUPS_URL}/{group['id']}",
        headers=auth_header(token),
    )
    assert detail.status_code == 200
    assert "password_hash" not in detail.text
    assert "password" not in detail.text
    assert RAW_PASSWORD not in detail.text


def test_groups_support_cookie_authentication(
    client: TestClient, db_session: Session
) -> None:
    """Group endpoints authenticate seamlessly via HttpOnly cookies as well as Bearer tokens."""
    # Login sets cookies in client.cookies automatically
    client.post(
        REGISTER_URL,
        json={"email": "cookie_user@example.com", "password": RAW_PASSWORD},
    )
    client.post(
        LOGIN_URL,
        json={"email": "cookie_user@example.com", "password": RAW_PASSWORD},
    )

    # Post group using cookie auth without explicit Bearer header
    csrf_token = client.cookies.get("velle_csrf_token")
    assert csrf_token
    create_res = client.post(
        GROUPS_URL,
        json={"name": "Cookie Group"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create_res.status_code == 201
    group_id = create_res.json()["id"]

    # List groups using cookie auth
    list_res = client.get(GROUPS_URL)
    assert list_res.status_code == 200
    assert any(g["id"] == group_id for g in list_res.json())

    # Get group details using cookie auth
    detail_res = client.get(f"{GROUPS_URL}/{group_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Cookie Group"
