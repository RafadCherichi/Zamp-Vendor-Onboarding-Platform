"""Safety checks for a shared, publicly reachable synthetic demo."""

import pytest

from app.api.endpoints import demo
from app.config import Settings, settings
from app.storage.local import get_storage_adapter


def _token(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_reset_requires_admin_and_does_not_run_for_other_roles(client, monkeypatch):
    calls = []
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(demo, "reset_and_seed_demo", lambda db: calls.append(True) or {"success": True})

    assert client.post("/api/demo/reset").status_code == 401
    for email in ("vendor.clean@tatasupply.in", "reviewer@apex.com"):
        token = _token(client, email)
        response = client.post("/api/demo/reset", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
    assert calls == []

    admin_token = _token(client, "admin@apex.com")
    response = client.post("/api/demo/reset", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert calls == [True]


def test_reset_stays_disabled_in_production_even_for_demo_admin(client, monkeypatch):
    calls = []
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(demo, "reset_and_seed_demo", lambda db: calls.append(True))
    admin_token = _token(client, "admin@apex.com")

    response = client.post("/api/demo/reset", headers={"Authorization": f"Bearer {admin_token}"})

    assert response.status_code == 404
    assert calls == []


def test_production_rejects_known_development_secret():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SECRET_KEY="insecure-dev-secret-key-please-change-in-production-random-bytes",
        )


def test_unknown_storage_backend_fails_instead_of_using_local(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "unsupported")
    with pytest.raises(ValueError, match="STORAGE_BACKEND"):
        get_storage_adapter()
