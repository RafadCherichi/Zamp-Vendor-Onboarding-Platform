"""Contract between bank text extraction and the approval consistency layer."""

from types import SimpleNamespace

import pytest

from app.services.extraction.extractors.bank import extract_bank_fields
from app.services.validation.layer_b_consistency import run_layer_b_checks


@pytest.mark.parametrize(
    "entered_account,expected_status",
    [
        ("123456785678", "PASSED"),
        ("123456785679", "FAILED"),
    ],
)
def test_extracted_bank_account_is_compared_with_entered_account(
    entered_account, expected_status
):
    extracted = extract_bank_fields(
        "CANCELLED CHEQUE\nAccount No: 123456785678\nIFSC: HDFC0001234\n"
        "Account Name: Tata Industrial Supplies Private Limited"
    )
    extraction = SimpleNamespace(
        raw_text="CANCELLED CHEQUE",
        fields=[SimpleNamespace(field_name=f.field_name, extracted_value=f.extracted_value) for f in extracted],
    )
    version = SimpleNamespace(id="version-1", extraction_result=extraction)
    bank_doc = SimpleNamespace(
        id="document-1", document_type="BANK_PROOF", current_version=version
    )
    application = SimpleNamespace(
        documents=[bank_doc], pan=None, gstin=None, is_gst_registered=False,
        legal_name="Tata Industrial Supplies Pvt Ltd", constitution="PVT_LTD",
        bank_account_number=entered_account, bank_ifsc="HDFC0001234",
        bank_account_holder_name="Tata Industrial Supplies Pvt Ltd",
    )

    findings = run_layer_b_checks(application)
    account = [f for f in findings if f["check_id"] == "B_BANK_ACCOUNT_NUM_MATCH"]
    assert len(account) == 1
    assert account[0]["status"] == expected_status


def test_unreadable_bank_account_does_not_disappear_from_findings():
    extraction = SimpleNamespace(raw_text="CANCELLED CHEQUE", fields=[])
    version = SimpleNamespace(id="version-1", extraction_result=extraction)
    bank_doc = SimpleNamespace(id="document-1", document_type="BANK_PROOF", current_version=version)
    application = SimpleNamespace(
        documents=[bank_doc], pan=None, gstin=None, is_gst_registered=False,
        legal_name="Tata Industrial Supplies Pvt Ltd", constitution="PVT_LTD",
        bank_account_number="123456785678", bank_ifsc="HDFC0001234",
        bank_account_holder_name="Tata Industrial Supplies Pvt Ltd",
    )

    findings = run_layer_b_checks(application)
    account = [f for f in findings if f["check_id"] == "B_BANK_ACCOUNT_NUM_MATCH"]
    assert len(account) == 1
    assert account[0]["status"] == "UNVERIFIED"
