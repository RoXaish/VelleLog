from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """
    Verify GET /api/health returns HTTP 200 and exact JSON {"status": "ok"}.
    Endpoint must be accessible without authentication.
    """
    response = client.get("/api/health")

    # Assert HTTP status code is 200
    assert response.status_code == 200

    # Assert JSON payload matches expected format exactly
    assert response.json() == {"status": "ok"}
