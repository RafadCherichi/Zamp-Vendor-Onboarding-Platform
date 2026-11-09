"""Complete seeded correction journey in a private, disposable database."""
import pytest
from pathlib import Path


@pytest.mark.parametrize("replace_proof", [False, True])
def test_two_requests_correction_review_and_approval(tmp_path, monkeypatch, replace_proof):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from fastapi.testclient import TestClient
    from app.database import Base, get_db
    from app.main import app
    from app.config import settings
    from app.db.seed_demo import reset_and_seed_demo
    from app.models.application import Application
    from app.models.document import Document
    from app.models.validation import ValidationRun
    from app.services.review.decision_service import ReviewerDecisionService
    engine = create_engine(f"sqlite:///{(tmp_path / 'journey.db').as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "STORAGE_LOCAL_DIR", str(tmp_path / "uploads"))
    db = Session(engine)
    reset_and_seed_demo(db)
    from app.services.extraction.pipeline import run_pipeline_for_document_version
    def process_private_upload(version_id):
        with Session(engine) as worker:
            return run_pipeline_for_document_version(version_id, worker)
    monkeypatch.setattr("app.api.endpoints.applications.background_process_document", process_private_upload)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            def login(email):
                response = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
                assert response.status_code == 200
                return {"Authorization": "Bearer " + response.json()["access_token"]}
            # The warning example must contain its actual proof, not unrelated samples.
            logistics = db.get(Application, "app-warn-003")
            assert not [d.title for d in logistics.documents if d.is_required and d.status != "UPLOADED"]
            eligible, reasons = ReviewerDecisionService(db).check_approval_eligibility(logistics)
            assert not eligible
            assert not any("Mandatory document missing" in reason for reason in reasons)
            logistics_run = db.query(ValidationRun).filter_by(application_id=logistics.id, is_current=True).one()
            assert not [finding.check_name for finding in logistics_run.findings if finding.status == "FAILED"]

            vendor = login("vendor.mismatch@sharmaworks.in")
            reviewer = login("reviewer@apex.com")
            # Exercise the actual shipped autofill values and public files together.
            import re, json
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            source = (root / "frontend/src/components/vendor/demoAutofill.ts").read_text(encoding="utf-8")
            def object_value(name):
                text = re.search(name + r":\s*(\{.*?\n    \})", source, re.S).group(1)
                return json.loads(re.sub(r"(\b[a-zA-Z_]\w*)\s*:", r'"\1":', text).replace("'", '"').replace(",\n    }", "\n    }"))
            draft = object_value("draft")
            files = object_value("documents")
            baseline = login("vendor@apexcomponents.com")
            draft.update(declaration_accurate_info=True, declaration_authorised_rep=True, declaration_verification_consent=True)
            response = client.patch("/api/applications/app-apex-base-01", headers=baseline, json=draft)
            assert response.status_code == 200, response.text
            for document_type, filename in files.items():
                content = (root / "frontend/public/demo-documents" / filename).read_bytes()
                response = client.post(f"/api/applications/app-apex-base-01/documents/{document_type}/upload", headers=baseline, files={"file": (filename, content, "application/pdf")})
                assert response.status_code == 200, response.text
            response = client.post("/api/applications/app-apex-base-01/submit", headers=baseline)
            assert response.status_code == 200, response.text
            base = db.get(Application, "app-apex-base-01")
            db.refresh(base)
            eligible, reasons = ReviewerDecisionService(db).check_approval_eligibility(base)
            assert eligible, reasons

            case = db.get(Application, "app-mism-002")
            assert not [d.title for d in case.documents if d.is_required and d.status != "UPLOADED"]
            issues = client.get("/api/exceptions/?application_id=app-mism-002", headers=vendor).json()
            bank = next(item for item in issues if item["related_field_name"] == "bank_account_number")
            assert len(issues) == 1
            requested = client.post("/api/applications/app-mism-002/request-clarification", headers=reviewer, json={"instructions": "Confirm that you are authorised to supply this information."})
            assert requested.status_code == 200
            issues = client.get("/api/exceptions/?application_id=app-mism-002", headers=vendor).json()
            second = next(item for item in issues if item["id"] != bank["id"])
            correction = {"field_name": "bank_account_number", "new_field_value": "60200012345678", "explanation": "Corrected the account number to match the attached cheque."}
            if replace_proof:
                proof = Path(__file__).resolve().parents[2] / "frontend/public/demo-documents/bank_sharma.pdf"
                response = client.post("/api/applications/app-mism-002/documents/BANK_PROOF/upload", headers=vendor,
                    data={**correction, "exception_id": bank["id"]}, files={"file": (proof.name, proof.read_bytes(), "application/pdf")})
            else:
                response = client.post(f"/api/exceptions/{bank['id']}/correct", headers=vendor, json=correction)
            assert response.status_code == 200, response.text
            db.refresh(case)
            assert case.bank_account_number == "60200012345678"
            assert case.status == "ACTION_REQUIRED"
            queue = client.get("/api/applications/queue", headers=reviewer).json()
            row = next(item for item in queue["items"] if item["id"] == case.id)
            assert row["vendor_replied"] is True
            assert row["ready_for_approval"] is False
            result = client.post(f"/api/exceptions/{bank['id']}/resolve", headers=reviewer, json={"target_status": "RESOLVED", "reason": "Corrected account matches proof and independent registry.", "resolution_type": "CORRECTED_BY_VENDOR", "notes": "Compared the new account value with the uploaded cheque."})
            assert result.status_code == 200, result.text
            assert client.post("/api/applications/app-mism-002/approve", headers=reviewer, json={}).status_code == 400
            response = client.post(f"/api/exceptions/{second['id']}/correct", headers=vendor, json={"explanation": "I confirm I am the authorised proprietor."})
            assert response.status_code == 200, response.text
            result = client.post(f"/api/exceptions/{second['id']}/resolve", headers=reviewer, json={"target_status": "RESOLVED", "reason": "Authority confirmed.", "resolution_type": "VERIFIED_MANUALLY", "notes": "Reviewed the supplier's confirmation."})
            assert result.status_code == 200, result.text
            response = client.post("/api/applications/app-mism-002/approve", headers=reviewer, json={"notes": "Both requested corrections reviewed."})
            assert response.status_code == 200, response.text
            current = client.get("/api/applications/current", headers=vendor).json()
            assert current["status"] == "APPROVED"
            assert current["reviewed_at"]
            notices = client.get("/api/notifications/", headers=vendor).json()
            assert any("Approved" in notice["title"] and notice["entity_id"] == case.id for notice in notices)
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()
