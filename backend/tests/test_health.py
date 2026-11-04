def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
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
