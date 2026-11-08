"""The live run view must report stages reached by actual work."""

from app.database import SessionLocal
from app.models.application import Application
from app.models.document import Document, DocumentVersion
from app.models.extraction import DocumentProcessingJob
from app.services.extraction import pipeline


def _token(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_processing_status_is_scoped_and_tracks_new_version(client, db_session):
    app = db_session.query(Application).filter_by(reference_number="APP-2026-CLEAN-001").one()
    document = db_session.query(Document).filter_by(application_id=app.id, document_type="PAN_PROOF").one()
    version = db_session.query(DocumentVersion).filter_by(id=document.current_version_id).one()
    token = _token(client, "vendor.clean@tatasupply.in")
    url = f"/api/applications/{app.id}/documents/PAN_PROOF/processing"

    current = client.get(url, params={"after_version": 0}, headers={"Authorization": f"Bearer {token}"})
    assert current.status_code == 200
    assert current.json()["version_number"] == version.version_number
    assert current.json()["stage"] in {"COMPLETE", "NEEDS_REVIEW", "FAILED"}

    waiting = client.get(
        url,
        params={"after_version": version.version_number},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert waiting.status_code == 200
    assert waiting.json()["stage"] == "SENDING_FILE"

    other_vendor = _token(client, "vendor.mismatch@sharmaworks.in")
    denied = client.get(url, headers={"Authorization": f"Bearer {other_vendor}"})
    assert denied.status_code == 404
    assert client.get(url).status_code == 401


def test_pipeline_persists_stage_before_each_operation(db_session, monkeypatch):
    app = db_session.query(Application).filter_by(reference_number="APP-2026-CLEAN-001").one()
    document = db_session.query(Document).filter_by(application_id=app.id, document_type="PAN_PROOF").one()
    version_id = document.current_version_id
    observed = []

    def current_stage():
        with SessionLocal() as independent_session:
            job = independent_session.query(DocumentProcessingJob).filter_by(document_version_id=version_id).one()
            return job.stage

    original_ocr = pipeline.extract_document_text
    original_classify = pipeline.classify_document
    original_extract = pipeline.GeminiExtractionProvider.extract

    def reading(*args, **kwargs):
        observed.append(current_stage())
        return original_ocr(*args, **kwargs)

    def classifying(*args, **kwargs):
        observed.append(current_stage())
        return original_classify(*args, **kwargs)

    def extracting(self, *args, **kwargs):
        observed.append(current_stage())
        return original_extract(self, *args, **kwargs)

    monkeypatch.setattr(pipeline, "extract_document_text", reading)
    monkeypatch.setattr(pipeline, "classify_document", classifying)
    monkeypatch.setattr(pipeline.GeminiExtractionProvider, "extract", extracting)

    result = pipeline.run_pipeline_for_document_version(version_id, db_session, force_reprocess=True)

    assert result is not None
    assert observed == ["READING_TEXT", "CLASSIFYING", "EXTRACTING_FIELDS"]
    assert current_stage() in {"COMPLETE", "NEEDS_REVIEW"}
