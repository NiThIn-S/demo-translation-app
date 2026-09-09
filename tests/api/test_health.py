def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "version" in data


def test_health_returns_request_id(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "test-request"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
