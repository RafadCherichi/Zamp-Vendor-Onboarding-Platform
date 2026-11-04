import io
import json
import secrets
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app.database import SessionLocal
from app.models.document import Document, DocumentVersion, DocumentTypeEnum
from app.models.extraction import (
    DocumentProcessingJob,
    DocumentExtractionResult,
    ExtractedField,
    ProcessingStatusEnum,
)
from app.services.ocr.engine import extract_document_text
from app.services.classification.classifier import classify_document
from app.services.extraction.providers.local import LocalDeterministicProvider
from app.services.extraction.pipeline import run_pipeline_for_document_version
from app.utils.synthetic_docs import (
    generate_synthetic_pan_pdf,
    generate_synthetic_pan_image,
    generate_synthetic_gst_pdf,
    generate_synthetic_bank_cheque_image,
    generate_synthetic_udyam_pdf,
    generate_synthetic_coi_pdf,
    generate_synthetic_unreadable_image,
)


def get_token(client, email: str, password: str = "Password123!") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# -------------------------------------------------------------
# 1. OCR & Text Extraction Tests
# -------------------------------------------------------------

def test_pdf_selectable_text_extraction(tmp_path):
    pdf_path = str(tmp_path / "test_pan.pdf")
    generate_synthetic_pan_pdf(pdf_path)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = extract_document_text(pdf_bytes, "application/pdf")
    assert result.is_unreadable is False
    assert result.primary_method == "PDF_TEXT"
    assert result.page_count == 1
    assert "INCOME TAX DEPARTMENT" in result.full_text
    assert "AAPFU0938L" in result.full_text
    assert "VIKRAM MALHOTRA" in result.full_text
    assert result.average_confidence >= 0.95


def test_image_ocr_neural_vision(tmp_path):
    png_path = str(tmp_path / "test_cheque.png")
    generate_synthetic_bank_cheque_image(png_path)

    with open(png_path, "rb") as f:
        img_bytes = f.read()

    result = extract_document_text(img_bytes, "image/png")
    assert result.is_unreadable is False
    assert result.primary_method == "OCR_VISION"
    assert result.page_count == 1
    assert "HDFC" in result.full_text.upper()
    assert "HDFC0000123" in result.full_text
    assert "9876543210123" in result.full_text
    assert result.average_confidence >= 0.80


def test_multi_page_pdf_processing(tmp_path):
    multi_pdf = str(tmp_path / "multi_page.pdf")
    c = canvas.Canvas(multi_pdf, pagesize=letter)
    c.drawString(100, 700, "Page 1 Content - Government of India GST Form REG-06 GSTIN 27AAPFU0938L1ZV")
    c.showPage()
    c.drawString(100, 700, "Page 2 Content - Annexure A Details and Director Signatures")
    c.save()

    with open(multi_pdf, "rb") as f:
        pdf_bytes = f.read()

    result = extract_document_text(pdf_bytes, "application/pdf")
    assert result.page_count == 2
    assert "Page 1 Content" in result.pages[0].text
    assert "Page 2 Content" in result.pages[1].text
    assert "--- Page Break ---" in result.full_text


def test_unreadable_and_corrupt_file_handling(tmp_path):
    noise_path = str(tmp_path / "noise.png")
    generate_synthetic_unreadable_image(noise_path)

    with open(noise_path, "rb") as f:
        noise_bytes = f.read()

    result = extract_document_text(noise_bytes, "image/png")
    assert result.is_unreadable is True
    assert result.average_confidence == 0.0

    # Corrupt non-PDF bytes claiming to be PDF
    corrupt_res = extract_document_text(b"NOT_A_REAL_PDF", "application/pdf")
    assert corrupt_res.is_unreadable is True
    assert corrupt_res.error_message is not None


# -------------------------------------------------------------
# 2. Document Classification Tests
# -------------------------------------------------------------

def test_document_classification_correct_types():
    # 1. PAN
    pan_text = "INCOME TAX DEPARTMENT GOVT. OF INDIA Permanent Account Number Card PAN: AAPFU0938L Name: VIKRAM MALHOTRA"
    res_pan = classify_document(pan_text, "PAN_PROOF")
    assert res_pan.predicted_type == "PAN_PROOF"
    assert res_pan.is_type_match is True
    assert res_pan.confidence >= 0.85

    # 2. GST
    gst_text = "Government of India Form GST REG-06 Registration Certificate Registration Number (GSTIN): 27AAPFU0938L1ZV Legal Name: Apex Fasteners"
    res_gst = classify_document(gst_text, "GST_CERTIFICATE")
    assert res_gst.predicted_type == "GST_CERTIFICATE"
    assert res_gst.is_type_match is True

    # 3. Bank Cheque
    bank_text = "HDFC BANK LTD IFSC: HDFC0000123 A/C NO: 9876543210123 CANCELLED Pay to: Apex Components"
    res_bank = classify_document(bank_text, "BANK_PROOF")
    assert res_bank.predicted_type == "BANK_PROOF"
    assert res_bank.is_type_match is True

    # 4. Udyam
    udyam_text = "Ministry of Micro, Small and Medium Enterprises UDYAM REGISTRATION CERTIFICATE UDYAM-MH-02-0012345"
    res_udyam = classify_document(udyam_text, "UDYAM_CERTIFICATE")
    assert res_udyam.predicted_type == "UDYAM_CERTIFICATE"
    assert res_udyam.is_type_match is True

    # 5. COI
    coi_text = "MINISTRY OF CORPORATE AFFAIRS Certificate of Incorporation Corporate Identity Number (CIN): U72200KA2020PTC123456"
    res_coi = classify_document(coi_text, "CONSTITUTION_PROOF")
    assert res_coi.predicted_type == "CONSTITUTION_PROOF"
    assert res_coi.is_type_match is True


def test_document_classification_mismatch_flagged():
    # Vendor mistakenly uploads GST certificate to PAN slot
    gst_text = "Government of India Form GST REG-06 Registration Certificate Registration Number (GSTIN): 27AAPFU0938L1ZV"
    res = classify_document(gst_text, target_document_type="PAN_PROOF")

    assert res.predicted_type == "GST_CERTIFICATE"
    assert res.is_type_match is False
    assert "Uploaded to 'PAN_PROOF' slot but content strongly matches 'GST_CERTIFICATE'" in res.reason


# -------------------------------------------------------------
# 3. Structured Field Extraction Tests
# -------------------------------------------------------------

def test_structured_field_extraction_pan():
    provider = LocalDeterministicProvider()
    pan_text = "INCOME TAX DEPARTMENT GOVT OF INDIA Permanent Account Number Card\nName: VIKRAM MALHOTRA\nFather's Name: RAJESH MALHOTRA\nDate of Birth: 12/04/1985\nPAN: AAPFU0938L"
    fields = provider.extract(pan_text, "PAN_PROOF")
    field_map = {f.field_name: f for f in fields}

    assert "pan_number" in field_map
    assert field_map["pan_number"].normalized_value == "AAPFU0938L"
    assert field_map["pan_number"].confidence_score >= 0.95
    assert field_map["pan_number"].evidence_text is not None

    assert "holder_name" in field_map
    assert "VIKRAM MALHOTRA" in field_map["holder_name"].normalized_value.upper()

    assert "date_of_birth_or_incorporation" in field_map
    assert field_map["date_of_birth_or_incorporation"].normalized_value == "12/04/1985"


def test_structured_field_extraction_gst():
    provider = LocalDeterministicProvider()
    gst_text = (
        "Government of India\nForm GST REG-06\nRegistration Certificate\n"
        "Registration Number (GSTIN): 27AAPFU0938L1ZV\n"
        "Legal Name: Apex Components & Fasteners\n"
        "Trade Name: Apex Fasteners\n"
        "Constitution of Business: Sole Proprietorship\n"
        "Date of Liability: 01/07/2017\n"
        "Address of Principal Place of Business:\nPlot 42, Wagle Industrial Estate, Road No. 16, Thane 400604"
    )
    fields = provider.extract(gst_text, "GST_CERTIFICATE")
    field_map = {f.field_name: f for f in fields}

    assert field_map["gstin"].normalized_value == "27AAPFU0938L1ZV"
    assert field_map["legal_name"].normalized_value == "Apex Components & Fasteners"
    assert field_map["trade_name"].normalized_value == "Apex Fasteners"
    assert field_map["constitution_of_business"].normalized_value == "Sole Proprietorship"
    assert field_map["registration_date"].normalized_value == "01/07/2017"


def test_structured_field_extraction_bank():
    provider = LocalDeterministicProvider()
    bank_text = "HDFC BANK LTD\nIFSC: HDFC0000123\nA/C NO: 9876543210123\nCANCELLED\nPay to: Apex Components & Fasteners"
    fields = provider.extract(bank_text, "BANK_PROOF")
    field_map = {f.field_name: f for f in fields}

    assert field_map["ifsc_code"].normalized_value == "HDFC0000123"
    assert field_map["bank_account_number"].normalized_value == "9876543210123"
    assert field_map["bank_name"].normalized_value == "Hdfc Bank"


# -------------------------------------------------------------
# 4. Pipeline Execution, API & Security Tests
# -------------------------------------------------------------

def test_full_pipeline_upload_and_extraction_endpoint(client, tmp_path):
    proc_token = get_token(client, "procurement@apex.com")
    vendor_email = f"extract_{secrets.token_hex(4)}@testpipe.in"

    # 1. Create and accept invitation
    inv_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Pipeline Test Corp", "vendor_email": vendor_email, "days_valid": 5},
    )
    raw_token = inv_resp.json()["demo_invitation_url"].replace("/invite/", "")
    acc_resp = client.post(f"/api/invitations/token/{raw_token}/accept", json={"password": "Password123!"})
    vendor_token = acc_resp.json()["access_token"]
    app_id = acc_resp.json()["application_id"]

    # 2. Generate and upload synthetic PAN PDF
    pan_file = str(tmp_path / "pan.pdf")
    generate_synthetic_pan_pdf(pan_file)
    with open(pan_file, "rb") as f:
        upload_resp = client.post(
            f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files={"file": ("pan_card.pdf", f, "application/pdf")},
        )

    assert upload_resp.status_code == 200
    slot_data = upload_resp.json()
    doc_id = slot_data["id"]
    assert slot_data["processing_status"] in ["EXTRACTED", "NEEDS_REVIEW"]
    assert slot_data["detected_document_type"] == "PAN_PROOF"
    assert slot_data["is_type_match"] is True

    # Check that PAN in summary is masked for security
    pan_summary = slot_data["extracted_fields_summary"].get("pan_number", "")
    assert "*****" in pan_summary

    # 3. Call full extraction detail endpoint
    ext_resp = client.get(
        f"/api/applications/{app_id}/documents/{doc_id}/extraction",
        headers={"Authorization": f"Bearer {vendor_token}"},
    )
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["detected_document_type"] == "PAN_PROOF"
    assert ext_data["is_type_match"] is True
    assert len(ext_data["fields"]) >= 2

    # 4. Idempotency & Reprocess
    reprocess_resp = client.post(
        f"/api/applications/{app_id}/documents/{doc_id}/reprocess",
        headers={"Authorization": f"Bearer {vendor_token}"},
    )
    assert reprocess_resp.status_code == 200
    assert reprocess_resp.json()["id"] == ext_data["id"]


def test_type_mismatch_upload_triggers_needs_review(client, tmp_path):
    proc_token = get_token(client, "procurement@apex.com")
    vendor_email = f"mismatch_{secrets.token_hex(4)}@testpipe.in"

    inv_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Mismatch Test Vendor", "vendor_email": vendor_email, "days_valid": 5},
    )
    raw_token = inv_resp.json()["demo_invitation_url"].replace("/invite/", "")
    acc_resp = client.post(f"/api/invitations/token/{raw_token}/accept", json={"password": "Password123!"})
    vendor_token = acc_resp.json()["access_token"]
    app_id = acc_resp.json()["application_id"]

    # Upload a GST certificate file to the PAN_PROOF slot
    gst_file = str(tmp_path / "gst.pdf")
    generate_synthetic_gst_pdf(gst_file)
    with open(gst_file, "rb") as f:
        bad_upload = client.post(
            f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files={"file": ("gst_as_pan.pdf", f, "application/pdf")},
        )

    assert bad_upload.status_code == 200
    bad_data = bad_upload.json()
    # Should flag NEEDS_REVIEW and document mismatch
    assert bad_data["processing_status"] == "NEEDS_REVIEW"
    assert bad_data["detected_document_type"] == "GST_CERTIFICATE"
    assert bad_data["is_type_match"] is False
    assert any("Document type mismatch" in flag for flag in bad_data["review_flags"])


def test_cross_tenant_extraction_isolation(client, tmp_path):
    proc_token = get_token(client, "procurement@apex.com")
    vendor_email = f"isolation_{secrets.token_hex(4)}@testpipe.in"

    inv_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Isolation Corp", "vendor_email": vendor_email, "days_valid": 5},
    )
    raw_token = inv_resp.json()["demo_invitation_url"].replace("/invite/", "")
    acc_resp = client.post(f"/api/invitations/token/{raw_token}/accept", json={"password": "Password123!"})
    vendor_token = acc_resp.json()["access_token"]
    app_id = acc_resp.json()["application_id"]

    pan_file = str(tmp_path / "pan.pdf")
    generate_synthetic_pan_pdf(pan_file)
    with open(pan_file, "rb") as f:
        up_resp = client.post(
            f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files={"file": ("pan.pdf", f, "application/pdf")},
        )
    doc_id = up_resp.json()["id"]

    # Tenant B procurement officer attempts to view Tenant A's document extraction
    tenant_b_token = get_token(client, "procurement@zenith.com")
    leak_resp = client.get(
        f"/api/applications/{app_id}/documents/{doc_id}/extraction",
        headers={"Authorization": f"Bearer {tenant_b_token}"},
    )
    # Must be 404 or 403 due to organisation scoping
    assert leak_resp.status_code in [403, 404]
