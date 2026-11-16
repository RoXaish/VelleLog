from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import create_access_token

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
LOGOUT_URL = "/api/auth/logout"
ME_URL = "/api/auth/me"
HEALTH_URL = "/api/health"

AUTH_COOKIE = "velle_access_token"
CSRF_COOKIE = "velle_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
RAW_PASSWORD = "s3cure-passphrase"


def register_user(
    client: TestClient,
    email: str = "cookie@example.com",
) -> dict:
    response = client.post(
        REGISTER_URL,
        json={"email": email, "password": RAW_PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def login_user(client: TestClient, email: str = "cookie@example.com") -> dict:
    response = client.post(
        LOGIN_URL,
        json={"email": email, "password": RAW_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()


def raw_set_cookies(response) -> dict[str, str]:
    headers = {}
    for header in response.headers.get_list("set-cookie"):
        name = header.split(";", 1)[0].split("=", 1)[0]
        headers[name] = header
    return headers


def test_login_sets_cookie_attributes(client: TestClient, db_session: Session) -> None:
    register_user(client)

    login_response = client.post(
        LOGIN_URL,
        json={"email": "cookie@example.com", "password": RAW_PASSWORD},
    )

    cookies = raw_set_cookies(login_response)
    assert set(cookies) == {AUTH_COOKIE, CSRF_COOKIE}

    auth_cookie = cookies[AUTH_COOKIE].lower()
    expected_max_age = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert "httponly" in auth_cookie
    assert "samesite=lax" in auth_cookie
    assert "path=/api;" in auth_cookie
    assert f"max-age={expected_max_age}" in auth_cookie
    assert "secure" not in auth_cookie

    csrf_cookie = cookies[CSRF_COOKIE].lower()
    assert "httponly" not in csrf_cookie
    assert "samesite=lax" in csrf_cookie
    assert "path=/;" in csrf_cookie
    assert "path=/api" not in csrf_cookie
    assert f"max-age={expected_max_age}" in csrf_cookie


def test_login_marks_cookies_secure_when_configured(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_user(client)
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)

    login_response = client.post(
        LOGIN_URL,
        json={"email": "cookie@example.com", "password": RAW_PASSWORD},
    )

    cookies = raw_set_cookies(login_response)
    assert "secure" in cookies[AUTH_COOKIE].lower()
    assert "secure" in cookies[CSRF_COOKIE].lower()


def test_cookie_authenticates_me(client: TestClient, db_session: Session) -> None:
    user = register_user(client)
    login_user(client)

    response = client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert "password" not in response.text


def test_logout_clears_cookies_and_ends_session(
    client: TestClient, db_session: Session
) -> None:
    register_user(client)
    login_user(client)
    old_auth_cookie = client.cookies.get(AUTH_COOKIE)
    csrf_token = client.cookies.get(CSRF_COOKIE)
    assert old_auth_cookie and csrf_token

    logout_response = client.post(
        LOGOUT_URL,
        headers={CSRF_HEADER: csrf_token},
    )

    assert logout_response.status_code == 204
    cookies = raw_set_cookies(logout_response)
    assert "max-age=0" in cookies[AUTH_COOKIE].lower()
    assert "max-age=0" in cookies[CSRF_COOKIE].lower()

    assert client.get(ME_URL).status_code == 401
    assert client.cookies.get(AUTH_COOKIE) is None
    assert client.cookies.get(CSRF_COOKIE) is None


def test_logout_without_csrf_token_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    register_user(client)
    login_user(client)

    response = client.post(LOGOUT_URL)

    assert response.status_code == 403
    assert client.get(ME_URL).status_code == 200


def test_logout_with_invalid_csrf_token_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    register_user(client)
    login_user(client)

    response = client.post(
        LOGOUT_URL,
        headers={CSRF_HEADER: "not-the-issued-token"},
    )

    assert response.status_code == 403
    assert client.get(ME_URL).status_code == 200


@pytest.mark.parametrize(
    "token_factory",
    [
        lambda user_id: "not-a-jwt",
        lambda user_id: create_access_token(
            subject=user_id,
            expires_delta=timedelta(seconds=-1),
        ),
    ],
)
def test_invalid_or_expired_auth_cookie_is_rejected(
    client: TestClient,
    db_session: Session,
    token_factory,
) -> None:
    user = register_user(client)
    client.cookies.set(AUTH_COOKIE, token_factory(user["id"]), path="/api")

    assert client.get(ME_URL).status_code == 401


def test_bearer_token_takes_precedence_over_cookie(
    client: TestClient, db_session: Session
) -> None:
    first_user = register_user(client, "first@example.com")
    login_user(client, "first@example.com")
    first_cookie = client.cookies.get(AUTH_COOKIE)
    assert first_cookie

    second_user = register_user(client, "second@example.com")
    second_login = login_user(client, "second@example.com")
    second_token = second_login["access_token"]

    client.cookies.set(AUTH_COOKIE, first_cookie, path="/api")
    assert client.get(ME_URL).json()["id"] == first_user["id"]

    response = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == second_user["id"]


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer not-a-valid-token",
        "Basic dXNlcjpwYXNz",
    ],
)
def test_invalid_authorization_header_does_not_fall_back_to_cookie(
    client: TestClient,
    db_session: Session,
    authorization: str,
) -> None:
    register_user(client)
    login_user(client)
    assert client.get(ME_URL).status_code == 200

    response = client.get(ME_URL, headers={"Authorization": authorization})

    assert response.status_code == 401


def test_cors_allows_configured_origin_with_credentials(
    client: TestClient,
) -> None:
    origin = "http://frontend.test"
    assert origin in settings.CORS_ORIGINS

    response = client.get(HEALTH_URL, headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_allows_csrf_header(client: TestClient) -> None:
    origin = "http://frontend.test"

    response = client.options(
        LOGIN_URL,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "x-csrf-token" in response.headers["access-control-allow-headers"].lower()


def test_cors_rejects_unconfigured_origin(client: TestClient) -> None:
    response = client.get(
        HEALTH_URL,
        headers={"Origin": "http://untrusted.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
