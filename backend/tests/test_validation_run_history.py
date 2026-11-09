from datetime import datetime, timedelta, timezone

from app.models.application import Application
from app.models.validation import ValidationRun


def _token(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_validation_run_history_returns_real_outputs_and_newest_first(client, db_session):
    clean = db_session.query(Application).filter_by(reference_number="APP-2026-CLEAN-001").one()
    mismatch = db_session.query(Application).filter_by(reference_number="APP-2026-MISM-002").one()
    clean_run = db_session.query(ValidationRun).filter_by(application_id=clean.id).first()
    mismatch_run = db_session.query(ValidationRun).filter_by(application_id=mismatch.id).first()
    assert clean_run is not None and mismatch_run is not None

    mismatch_run.created_at = datetime.now(timezone.utc)
    clean_run.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    token = _token(client, "procurement@apex.com")
    response = client.get(
        "/api/applications/runs?limit=20",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    runs = response.json()
    assert runs[0]["id"] == mismatch_run.id
    assert {run["application_reference"] for run in runs} >= {
        "APP-2026-CLEAN-001",
        "APP-2026-MISM-002",
    }
    mismatch_item = next(run for run in runs if run["id"] == mismatch_run.id)
    assert mismatch_item["vendor_name"] == mismatch.legal_name
    assert mismatch_item["outcome"] == "PENDING"
    assert mismatch_item["failed_count"] > 0
    assert mismatch_item["reason"]
    assert mismatch_item["application_status"] == mismatch.status
    clean_item = next(run for run in runs if run["id"] == clean_run.id)
    assert clean_item["outcome"] == "PENDING"
    if clean_item["failed_count"] == clean_item["warning_count"] == 0:
        assert "checks passed" in clean_item["reason"].lower()
        assert "final decision" in clean_item["reason"].lower()


def test_validation_run_history_is_organisation_scoped(client):
    token = _token(client, "procurement@zenith.com")
    response = client.get(
        "/api/applications/runs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_validation_run_history_requires_authentication(client):
    response = client.get("/api/applications/runs")

    assert response.status_code == 401


def test_validation_run_history_detail_returns_the_selected_run(client, db_session):
    run = db_session.query(ValidationRun).first()
    assert run is not None
    token = _token(client, "procurement@apex.com")

    response = client.get(
        f"/api/applications/runs/{run.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == run.id
    assert detail["application_id"] == run.application_id
    assert detail["findings"]


def test_validation_run_history_detail_does_not_leak_across_organisations(client, db_session):
    run = db_session.query(ValidationRun).first()
    assert run is not None
    token = _token(client, "procurement@zenith.com")

    response = client.get(
        f"/api/applications/runs/{run.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_saved_failed_checks_stay_distinct_from_latest_approval(client, db_session):
    app = db_session.query(Application).filter_by(reference_number="APP-2026-MISM-002").one()
    old_status, old_reviewed = app.status, app.reviewed_at
    try:
        app.status = "APPROVED"
        app.reviewed_at = datetime.now(timezone.utc)
        db_session.commit()
        token = _token(client, "procurement@apex.com")
        response = client.get("/api/applications/runs?limit=100", headers={"Authorization": f"Bearer {token}"})
        item = next(row for row in response.json() if row["application_id"] == app.id and row["failed_count"] > 0)
        assert item["check_outcome"] == "NEEDS_REVIEW"
        assert item["application_status"] == "APPROVED"
        assert item["decision_at"]
        assert "reviewer approved" not in item["reason"].lower()
    finally:
        app.status, app.reviewed_at = old_status, old_reviewed
        db_session.commit()
