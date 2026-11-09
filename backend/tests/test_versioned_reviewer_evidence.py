"""A reviewer must be able to inspect the exact document version behind a claim."""

import io

from app.models.application import Application
from app.models.document import Document, DocumentVersion
from app.storage.local import get_storage_adapter


def test_preview_and_details_identify_exact_document_version(client, db_session):
    app = db_session.query(Application).filter_by(reference_number="APP-2026-CLEAN-001").one()
    document = db_session.query(Document).filter_by(application_id=app.id, document_type="PAN_PROOF").one()
    original = db_session.get(DocumentVersion, document.current_version_id)
    assert original is not None

    storage = get_storage_adapter()
    original_bytes = storage.get_file_bytes(original.storage_key)
    replacement_bytes = b"%PDF-1.4\n% synthetic replacement proof\n%%EOF"
    replacement_key = storage.save_file(
        io.BytesIO(replacement_bytes),
        f"org_{app.organisation_id}/app_{app.id}/synthetic_version_test.pdf",
        "application/pdf",
    )
    replacement = DocumentVersion(
        document_id=document.id,
        version_number=original.version_number + 1,
        storage_key=replacement_key,
        original_filename="synthetic_version_test.pdf",
        file_size_bytes=len(replacement_bytes),
        content_type="application/pdf",
        file_checksum="test-checksum",
    )
    db_session.add(replacement)
    db_session.flush()
    document.current_version_id = replacement.id
    db_session.commit()

    login = client.post(
        "/api/auth/login",
        json={"email": "admin@apex.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    url = f"/api/applications/{app.id}/documents/{document.id}/preview"

    old_preview = client.get(url, params={"version_id": original.id}, headers=headers)
    current_preview = client.get(url, params={"version_id": replacement.id}, headers=headers)
    wrong_version = client.get(url, params={"version_id": "unrelated-version"}, headers=headers)

    assert old_preview.status_code == 200
    assert old_preview.content == original_bytes
    assert current_preview.content == replacement_bytes
    assert wrong_version.status_code == 404

    details = client.get(f"/api/applications/{app.id}/details", headers=headers).json()
    version_links = [v["preview_url"] for d in details["documents"] if d["id"] == document.id for v in d["versions"]]
    assert len(version_links) >= 2
    assert all("version_id=" in link for link in version_links)


def test_preview_rejects_bearer_token_in_query_string(client, db_session):
    app = db_session.query(Application).filter_by(reference_number="APP-2026-CLEAN-001").one()
    document = db_session.query(Document).filter_by(application_id=app.id, document_type="PAN_PROOF").one()
    login = client.post("/api/auth/login", json={"email": "admin@apex.com", "password": "Password123!"})
    token = login.json()["access_token"]
    url = f"/api/applications/{app.id}/documents/{document.id}/preview"
    assert client.get(url, params={"token": token}).status_code == 401
    assert client.get(url, headers={"Authorization": f"Bearer {token}"}).status_code == 200
