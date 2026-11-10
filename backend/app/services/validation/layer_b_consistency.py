import re
from typing import List, Dict, Any, Optional
from app.models.application import Application
from app.models.document import Document, DocumentTypeEnum
from app.models.extraction import DocumentExtractionResult, ExtractedField
from app.models.validation import ValidationFinding, ValidationStatusEnum, ValidationSeverityEnum, ValidationLayerEnum
from app.services.validation.name_matching import compare_names, MatchTier
from app.services.verification.simulated import mask_id


def get_extracted_fields_by_doc_type(app: Application) -> Dict[str, Dict[str, Any]]:
    """
    Extracts a dictionary of key-value pairs for each document type associated
    with the current active version of documents in the application.
    Returns:
    {
       "PAN_PROOF": {"pan_number": "...", "pan_holder_name": "...", "doc_id": "...", "version_id": "..."},
       "GST_CERTIFICATE": {...},
       "BANK_PROOF": {...},
       "UDYAM_CERTIFICATE": {...}
    }
    """
    doc_data: Dict[str, Dict[str, Any]] = {}

    for doc in app.documents:
        # Get latest/current version
        current_version = doc.current_version
        if not current_version or not current_version.extraction_result:
            continue

        ext_result = current_version.extraction_result
        if isinstance(ext_result, list):
            ext_result = ext_result[0] if ext_result else None
        if not ext_result:
            continue

        fields_dict: Dict[str, Any] = {
            "__doc_id": doc.id,
            "__version_id": current_version.id,
            "__doc_type": doc.document_type,
            "__raw_text": ext_result.raw_text or "",
        }

        for fld in ext_result.fields:
            # Applicant-confirmed corrections take precedence for future checks;
            # the original OCR value remains available for evidence and audit.
            fields_dict[fld.field_name] = fld.vendor_corrected_value or fld.normalized_value or fld.extracted_value

        doc_data[doc.document_type] = fields_dict

    return doc_data


def run_layer_b_checks(app: Application) -> List[Dict[str, Any]]:
    """
    Executes Layer B cross-field, cross-document, and embedded identifier
    consistency checks.
    """
    findings: List[Dict[str, Any]] = []
    doc_data = get_extracted_fields_by_doc_type(app)

    # 1. GSTIN Embedded PAN vs Declared Application PAN
    app_pan = (app.pan or "").strip().upper()
    app_gstin = (app.gstin or "").strip().upper()

    if app.is_gst_registered and app_gstin and len(app_gstin) >= 12:
        embedded_pan = app_gstin[2:12]
        if app_pan:
            if embedded_pan == app_pan:
                findings.append({
                    "check_id": "B_GSTIN_EMBEDDED_PAN_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "GSTIN Embedded PAN vs Declared PAN",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.CRITICAL.value,
                    "submitted_value": mask_id(app_pan),
                    "extracted_value": mask_id(embedded_pan),
                    "external_value": None,
                    "evidence": f"Declared PAN '{mask_id(app_pan)}' exactly matches embedded PAN '{mask_id(embedded_pan)}' in GSTIN '{mask_id(app_gstin)}'.",
                    "explanation": "Statutory alignment confirmed: The 10-character PAN embedded within the 15-character GSTIN matches the declared business PAN.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "B_GSTIN_EMBEDDED_PAN_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "GSTIN Embedded PAN vs Declared PAN",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.CRITICAL.value,
                    "submitted_value": mask_id(app_pan),
                    "extracted_value": mask_id(embedded_pan),
                    "external_value": None,
                    "evidence": f"Declared PAN is '{mask_id(app_pan)}', but characters 3-12 of GSTIN '{mask_id(app_gstin)}' are '{mask_id(embedded_pan)}'.",
                    "explanation": f"Statutory mismatch: Embedded PAN '{mask_id(embedded_pan)}' in GSTIN does not match declared PAN '{mask_id(app_pan)}'. This indicates a cross-entity submission or registration error.",
                    "recommended_action": "Vendor must review the provided GSTIN and PAN certificates. If the vendor operates multiple entities, the correct entity's credentials must be submitted.",
                })

    # 2. Application PAN vs Extracted Document PAN
    pan_doc = doc_data.get(DocumentTypeEnum.PAN_PROOF.value)
    if pan_doc:
        extracted_pan = (pan_doc.get("pan_number") or "").strip().upper()
        doc_id = pan_doc.get("__doc_id")
        ver_id = pan_doc.get("__version_id")

        if extracted_pan:
            if app_pan and extracted_pan == app_pan:
                findings.append({
                    "check_id": "B_PAN_DOC_CROSS_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "Application PAN vs Extracted PAN Document",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.CRITICAL.value,
                    "source_document_id": doc_id,
                    "source_version_id": ver_id,
                    "submitted_value": mask_id(app_pan),
                    "extracted_value": mask_id(extracted_pan),
                    "external_value": None,
                    "evidence": f"Application PAN: '{mask_id(app_pan)}', Document OCR PAN: '{mask_id(extracted_pan)}'.",
                    "explanation": "The PAN entered in the application matches the PAN extracted from the uploaded PAN card proof.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "B_PAN_DOC_CROSS_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "Application PAN vs Extracted PAN Document",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.CRITICAL.value,
                    "source_document_id": doc_id,
                    "source_version_id": ver_id,
                    "submitted_value": mask_id(app_pan),
                    "extracted_value": mask_id(extracted_pan),
                    "external_value": None,
                    "evidence": f"Application PAN '{mask_id(app_pan)}' does not match Document OCR PAN '{mask_id(extracted_pan)}'.",
                    "explanation": "PAN discrepancy detected between form input and uploaded document. Possible wrong file uploaded or typographical error.",
                    "recommended_action": "Re-upload the matching PAN card or correct the application profile.",
                })
        else:
            findings.append({
                "check_id": "B_PAN_DOC_CROSS_MATCH",
                "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                "check_name": "Application PAN vs Extracted PAN Document",
                "status": ValidationStatusEnum.UNVERIFIED.value,
                "severity": ValidationSeverityEnum.MEDIUM.value,
                "source_document_id": doc_id,
                "source_version_id": ver_id,
                "submitted_value": mask_id(app_pan),
                "extracted_value": None,
                "external_value": None,
                "evidence": "PAN document uploaded but OCR failed to extract a structured 10-character PAN.",
                "source_document_id": doc_id,
                "source_version_id": ver_id,
                "explanation": "Document text was unreadable or field was missing in extracted results.",
                "recommended_action": "Manual review of uploaded PAN proof required.",
            })
    else:
        findings.append({
            "check_id": "B_PAN_DOC_CROSS_MATCH",
            "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
            "check_name": "Application PAN vs Extracted PAN Document",
            "status": ValidationStatusEnum.UNVERIFIED.value,
            "severity": ValidationSeverityEnum.HIGH.value,
            "submitted_value": mask_id(app_pan),
            "extracted_value": None,
            "external_value": None,
            "evidence": "No uploaded PAN proof document found.",
            "explanation": "PAN proof document has not been uploaded or processed yet.",
            "recommended_action": "Upload PAN card document.",
        })

    # 3. Application Legal Name vs Document Names (PAN Doc, GST Doc, Bank Doc)
    app_name = (app.legal_name or "").strip()
    
    # 3a. Legal Name vs PAN Document Name
    if pan_doc:
        pan_name = (pan_doc.get("pan_holder_name") or pan_doc.get("entity_name") or "").strip()
        doc_id = pan_doc.get("__doc_id")
        ver_id = pan_doc.get("__version_id")
        if pan_name:
            tier, score, reason = compare_names(app_name, pan_name, entity_type=app.constitution)
            if tier in [MatchTier.EXACT_MATCH, MatchTier.NORMALISED_MATCH]:
                status = ValidationStatusEnum.PASSED.value
                sev = ValidationSeverityEnum.MEDIUM.value
            elif tier == MatchTier.PROBABLE_MATCH:
                status = ValidationStatusEnum.WARNING.value
                sev = ValidationSeverityEnum.MEDIUM.value
            else:
                status = ValidationStatusEnum.FAILED.value
                sev = ValidationSeverityEnum.HIGH.value

            findings.append({
                "check_id": "B_NAME_PAN_DOC_MATCH",
                "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                "check_name": "Legal Name vs PAN Card Name",
                "status": status,
                "severity": sev,
                "source_document_id": doc_id,
                "source_version_id": ver_id,
                "submitted_value": app_name,
                "extracted_value": pan_name,
                "external_value": None,
                "evidence": f"Application: '{app_name}' vs PAN OCR: '{pan_name}' (Tier: {tier.value}, score: {score:.2f}).",
                "explanation": f"Name comparison result: {reason}",
                "recommended_action": "Review name match if flagged as warning or failure." if status != ValidationStatusEnum.PASSED.value else "No action required.",
            })

    # 3b. Legal Name vs GST Document Name
    gst_doc = doc_data.get(DocumentTypeEnum.GST_CERTIFICATE.value)
    if gst_doc:
        gst_legal = (gst_doc.get("legal_name") or "").strip()
        gst_trade = (gst_doc.get("trade_name") or "").strip()
        doc_id = gst_doc.get("__doc_id")
        ver_id = gst_doc.get("__version_id")

        target_gst_name = gst_legal or gst_trade
        if target_gst_name:
            tier, score, reason = compare_names(app_name, target_gst_name, entity_type=app.constitution)
            if tier in [MatchTier.EXACT_MATCH, MatchTier.NORMALISED_MATCH]:
                status = ValidationStatusEnum.PASSED.value
                sev = ValidationSeverityEnum.MEDIUM.value
            elif tier == MatchTier.PROBABLE_MATCH:
                status = ValidationStatusEnum.WARNING.value
                sev = ValidationSeverityEnum.MEDIUM.value
            else:
                status = ValidationStatusEnum.FAILED.value
                sev = ValidationSeverityEnum.HIGH.value

            findings.append({
                "check_id": "B_NAME_GST_DOC_MATCH",
                "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                "check_name": "Legal Name vs GST Certificate Name",
                "status": status,
                "severity": sev,
                "source_document_id": doc_id,
                "source_version_id": ver_id,
                "submitted_value": app_name,
                "extracted_value": target_gst_name,
                "external_value": None,
                "evidence": f"Application: '{app_name}' vs GST Certificate: '{target_gst_name}' (Tier: {tier.value}, score: {score:.2f}).",
                "explanation": f"GST name comparison result: {reason}",
                "recommended_action": "Verify if trade name / legal name discrepancy is acceptable." if status != ValidationStatusEnum.PASSED.value else "No action required.",
            })

    # 4. Bank Account vs Bank Proof Document
    bank_doc = doc_data.get(DocumentTypeEnum.BANK_PROOF.value)
    if bank_doc:
        # The local bank extractor emits bank_account_number. Accept the older
        # account_number key too for previously stored extraction results.
        ext_acc = (bank_doc.get("bank_account_number") or bank_doc.get("account_number") or "").strip()
        ext_ifsc = (bank_doc.get("ifsc_code") or "").strip().upper()
        ext_holder = (bank_doc.get("account_holder_name") or "").strip()
        doc_id = bank_doc.get("__doc_id")
        ver_id = bank_doc.get("__version_id")

        app_acc = (app.bank_account_number or "").strip()
        app_ifsc = (app.bank_ifsc or "").strip().upper()
        app_holder = (app.bank_account_holder_name or app.legal_name or "").strip()

        # Account number match
        if ext_acc and app_acc:
            clean_app_acc = re.sub(r"\D", "", app_acc)
            clean_ext_acc = re.sub(r"\D", "", ext_acc)
            if clean_app_acc == clean_ext_acc:
                findings.append({
                    "check_id": "B_BANK_ACCOUNT_NUM_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "Bank Account Number vs Bank Proof Document",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.CRITICAL.value,
                    "source_document_id": doc_id,
                    "source_version_id": ver_id,
                    "submitted_value": mask_id(app_acc),
                    "extracted_value": mask_id(ext_acc),
                    "external_value": None,
                    "evidence": f"Account number matches OCR extracted value from bank cheque/statement.",
                    "explanation": "Bank account number matches the uploaded bank proof document.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "B_BANK_ACCOUNT_NUM_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "Bank Account Number vs Bank Proof Document",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.CRITICAL.value,
                    "source_document_id": doc_id,
                    "source_version_id": ver_id,
                    "submitted_value": mask_id(app_acc),
                    "extracted_value": mask_id(ext_acc),
                    "external_value": None,
                    "evidence": f"Application account '{mask_id(app_acc)}' does not match extracted '{mask_id(ext_acc)}'.",
                    "explanation": "Discrepancy in bank account number between form input and bank document proof.",
                    "recommended_action": "Provide the correct bank account number or upload matching bank document.",
                })

        else:
            findings.append({
                "check_id": "B_BANK_ACCOUNT_NUM_MATCH",
                "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                "check_name": "Bank Account Number vs Bank Proof Document",
                "status": ValidationStatusEnum.UNVERIFIED.value,
                "severity": ValidationSeverityEnum.CRITICAL.value,
                "source_document_id": doc_id,
                "source_version_id": ver_id,
                "submitted_value": mask_id(app_acc) if app_acc else None,
                "extracted_value": None,
                "external_value": None,
                "evidence": "A readable account number was not available on the uploaded bank proof.",
                "explanation": "We could not compare the account number on the bank proof with the number entered in the form.",
                "recommended_action": "Upload a clear bank proof showing the account number, or ask the review team to verify it manually.",
            })

        # IFSC match
        if ext_ifsc and app_ifsc:
            if ext_ifsc == app_ifsc:
                findings.append({
                    "check_id": "B_BANK_IFSC_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "Bank IFSC vs Bank Proof Document",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.HIGH.value,
                    "source_document_id": doc_id,
                    "source_version_id": ver_id,
                    "submitted_value": app_ifsc,
                    "extracted_value": ext_ifsc,
                    "external_value": None,
                    "evidence": f"Application IFSC '{app_ifsc}' matches extracted '{ext_ifsc}'.",
                    "explanation": "IFSC code matches the uploaded bank proof document.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "B_BANK_IFSC_MATCH",
                    "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                    "check_name": "Bank IFSC vs Bank Proof Document",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.HIGH.value,
                    "source_document_id": doc_id,
                    "source_version_id": ver_id,
                    "submitted_value": app_ifsc,
                    "extracted_value": ext_ifsc,
                    "external_value": None,
                    "evidence": f"Application IFSC '{app_ifsc}' does not match extracted '{ext_ifsc}'.",
                    "explanation": "Bank IFSC code in application differs from bank document proof.",
                    "recommended_action": "Verify bank branch and update IFSC code.",
                })

        # Account holder name match
        if ext_holder and app_holder:
            tier, score, reason = compare_names(app_holder, ext_holder, entity_type=app.constitution)
            if tier in [MatchTier.EXACT_MATCH, MatchTier.NORMALISED_MATCH]:
                status = ValidationStatusEnum.PASSED.value
                sev = ValidationSeverityEnum.HIGH.value
            elif tier == MatchTier.PROBABLE_MATCH:
                status = ValidationStatusEnum.WARNING.value
                sev = ValidationSeverityEnum.MEDIUM.value
            else:
                status = ValidationStatusEnum.FAILED.value
                sev = ValidationSeverityEnum.HIGH.value

            findings.append({
                "check_id": "B_BANK_HOLDER_NAME_MATCH",
                "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                "check_name": "Bank Account Holder Name vs Bank Document",
                "status": status,
                "severity": sev,
                "source_document_id": doc_id,
                "source_version_id": ver_id,
                "submitted_value": app_holder,
                "extracted_value": ext_holder,
                "external_value": None,
                "evidence": f"Form: '{app_holder}' vs Bank Proof: '{ext_holder}' (Tier: {tier.value}, score: {score:.2f}).",
                "explanation": f"Bank holder name comparison result: {reason}",
                "recommended_action": "Ensure bank account is in the business entity's or proprietor's registered name." if status != ValidationStatusEnum.PASSED.value else "No action required.",
            })

    # 5. Cross-Document Consistency (PAN Doc vs GST Doc)
    if pan_doc and gst_doc:
        pan_name = (pan_doc.get("pan_holder_name") or pan_doc.get("entity_name") or "").strip()
        gst_name = (gst_doc.get("legal_name") or gst_doc.get("trade_name") or "").strip()
        if pan_name and gst_name:
            tier, score, reason = compare_names(pan_name, gst_name, entity_type=app.constitution)
            if tier in [MatchTier.EXACT_MATCH, MatchTier.NORMALISED_MATCH]:
                status = ValidationStatusEnum.PASSED.value
                sev = ValidationSeverityEnum.MEDIUM.value
            elif tier == MatchTier.PROBABLE_MATCH:
                status = ValidationStatusEnum.WARNING.value
                sev = ValidationSeverityEnum.MEDIUM.value
            else:
                status = ValidationStatusEnum.FAILED.value
                sev = ValidationSeverityEnum.HIGH.value

            findings.append({
                "check_id": "B_CROSS_DOC_PAN_GST_MATCH",
                "layer": ValidationLayerEnum.LAYER_B_CONSISTENCY.value,
                "check_name": "Cross-Document: PAN Card vs GST Certificate Name",
                "status": status,
                "severity": sev,
                "source_document_id": pan_doc.get("__doc_id"),
                "source_version_id": pan_doc.get("__version_id"),
                "submitted_value": None,
                "extracted_value": f"PAN Doc: '{pan_name}' | GST Doc: '{gst_name}'",
                "external_value": None,
                "evidence": f"PAN name: '{pan_name}' vs GST name: '{gst_name}' (Tier: {tier.value}, score: {score:.2f}).",
                "explanation": f"Inter-document consistency check: {reason}",
                "recommended_action": "Cross-check business name across statutory registrations." if status != ValidationStatusEnum.PASSED.value else "No action required.",
            })

    return findings
