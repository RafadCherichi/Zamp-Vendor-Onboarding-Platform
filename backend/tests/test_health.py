def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    if "text/html" in response.headers.get("content-type", ""):
        assert "id=\"root\"" in response.text
    else:
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["health"] == "/api/health"


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert "storage" in data
    assert data["storage"]["status"] == "ready"


def test_openapi_available(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/api/health" in schema["paths"]


def test_degraded_database_returns_unhealthy_http_status(client, monkeypatch):
    from app.api.endpoints import health

    monkeypatch.setattr(
        health,
        "check_database_connection",
        lambda: {"status": "error", "dialect": "sqlite", "latency_ms": 1.0, "error": "offline"},
    )
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
