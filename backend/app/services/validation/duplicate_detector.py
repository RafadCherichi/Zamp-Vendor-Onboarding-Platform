import json
import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.application import Application
from app.models.validation import (
    DuplicateSignal,
    ValidationFinding,
    ValidationStatusEnum,
    ValidationSeverityEnum,
    ValidationLayerEnum,
)
from app.services.validation.name_matching import compare_names, MatchTier
from app.services.verification.simulated import mask_id


def detect_duplicates_for_application(
    db: Session,
    app: Application,
) -> Tuple[List[DuplicateSignal], List[Dict[str, Any]]]:
    """
    Scans for duplicate candidates strictly within the same organisation.
    Generates explainable DuplicateSignal records without auto-rejection or auto-merge.
    Returns (signals_to_persist, validation_findings).
    """
    signals: List[DuplicateSignal] = []
    findings: List[Dict[str, Any]] = []

    # Query other applications within the same organisation
    other_apps = (
        db.query(Application)
        .filter(
            Application.organisation_id == app.organisation_id,
            Application.id != app.id,
        )
        .all()
    )

    clean_pan = (app.pan or "").strip().upper()
    clean_gstin = (app.gstin or "").strip().upper()
    clean_cin = (app.cin_llpin or "").strip().upper()
    clean_acc = re.sub(r"\D", "", app.bank_account_number or "")
    clean_phone = re.sub(r"\D", "", app.contact_mobile or "")
    clean_email = (app.contact_email or "").strip().lower()
    clean_pincode = (app.pincode or "").strip()

    candidate_matches: List[Dict[str, Any]] = []

    for other in other_apps:
        matching_attrs = []
        strength = "MODERATE"
        explanation_parts = []

        # 1. PAN Match (STRONG)
        other_pan = (other.pan or "").strip().upper()
        if clean_pan and other_pan and clean_pan == other_pan:
            matching_attrs.append("PAN")
            strength = "STRONG"
            explanation_parts.append(f"Identical PAN ({mask_id(clean_pan)})")

        # 2. GSTIN Match (STRONG)
        other_gstin = (other.gstin or "").strip().upper()
        if clean_gstin and other_gstin and clean_gstin == other_gstin:
            matching_attrs.append("GSTIN")
            strength = "STRONG"
            explanation_parts.append(f"Identical GSTIN ({mask_id(clean_gstin)})")

        # 3. CIN/LLPIN Match (STRONG)
        other_cin = (other.cin_llpin or "").strip().upper()
        if clean_cin and other_cin and clean_cin == other_cin:
            matching_attrs.append("CIN_LLPIN")
            strength = "STRONG"
            explanation_parts.append(f"Identical MCA Registration ({clean_cin})")

        # 4. Bank Account Match (STRONG)
        other_acc = re.sub(r"\D", "", other.bank_account_number or "")
        if clean_acc and other_acc and clean_acc == other_acc:
            matching_attrs.append("BANK_ACCOUNT")
            strength = "STRONG"
            explanation_parts.append(f"Identical Bank Account Number ({mask_id(clean_acc)})")

        # 5. Name + Location Match (MODERATE)
        if other.legal_name:
            tier, score, _ = compare_names(app.legal_name, other.legal_name, entity_type=app.constitution)
            other_pin = (other.pincode or "").strip()
            if score >= 0.85 and clean_pincode and clean_pincode == other_pin:
                matching_attrs.append("NAME_AND_PINCODE")
                if strength != "STRONG":
                    strength = "MODERATE"
                explanation_parts.append(f"Similar legal name ({score:.0%} match) in identical postal code ({clean_pincode})")

        # 6. Contact Details (WEAK/SUPPORTING)
        other_phone = re.sub(r"\D", "", other.contact_mobile or "")
        other_email = (other.contact_email or "").strip().lower()
        if clean_phone and other_phone and clean_phone == other_phone and "PAN" not in matching_attrs:
            matching_attrs.append("CONTACT_PHONE")
            explanation_parts.append("Shared authorised contact phone number")
        if clean_email and other_email and clean_email == other_email and "PAN" not in matching_attrs:
            matching_attrs.append("CONTACT_EMAIL")
            explanation_parts.append("Shared authorised contact email address")

        if matching_attrs:
            expl = f"Candidate match with application {other.reference_number}: {'; '.join(explanation_parts)}."
            rec_act = (
                "Review candidate application. Verify whether this is a duplicate submission, renewal, "
                "or separate business unit before taking approval action."
            )

            signal = DuplicateSignal(
                application_id=app.id,
                organisation_id=app.organisation_id,
                candidate_application_id=other.id,
                candidate_vendor_id=other.vendor_id,
                match_strength=strength,
                matching_attributes_json=json.dumps(matching_attrs),
                explanation=expl,
                recommended_action=rec_act,
            )
            signals.append(signal)
            candidate_matches.append({
                "candidate_ref": other.reference_number,
                "strength": strength,
                "matching_attrs": matching_attrs,
                "explanation": expl,
            })

    # Produce unified Layer D ValidationFinding
    if signals:
        has_strong = any(s.match_strength == "STRONG" for s in signals)
        candidate_refs = ", ".join(m["candidate_ref"] for m in candidate_matches)
        all_attrs = set()
        for m in candidate_matches:
            all_attrs.update(m["matching_attrs"])

        findings.append({
            "check_id": "D_DUPLICATE_DETECTION_CHECK",
            "layer": ValidationLayerEnum.LAYER_D_DUPLICATE.value,
            "check_name": "Organisation-Scoped Duplicate Vendor Check",
            "status": ValidationStatusEnum.WARNING.value if not has_strong else ValidationStatusEnum.FAILED.value,
            "severity": ValidationSeverityEnum.HIGH.value if has_strong else ValidationSeverityEnum.MEDIUM.value,
            "submitted_value": f"App Ref: {app.reference_number}",
            "extracted_value": None,
            "external_value": f"Matching Candidates: {candidate_refs}",
            "evidence": f"Found {len(signals)} candidate application(s) in organization sharing attributes: {', '.join(sorted(all_attrs))}.",
            "explanation": f"Duplicate signal detected. Shared identifiers ({', '.join(sorted(all_attrs))}) match existing application(s) {candidate_refs}.",
            "recommended_action": "Review duplicate candidate application(s) in reviewer verification dashboard before proceeding with approval.",
        })
    else:
        findings.append({
            "check_id": "D_DUPLICATE_DETECTION_CHECK",
            "layer": ValidationLayerEnum.LAYER_D_DUPLICATE.value,
            "check_name": "Organisation-Scoped Duplicate Vendor Check",
            "status": ValidationStatusEnum.PASSED.value,
            "severity": ValidationSeverityEnum.LOW.value,
            "submitted_value": f"App Ref: {app.reference_number}",
            "extracted_value": None,
            "external_value": "No duplicate candidates found",
            "evidence": "No matching PAN, GSTIN, CIN, bank account, or entity name found within organization.",
            "explanation": "No existing vendor application in this organisation shares key tax identifiers or bank account details.",
            "recommended_action": "No action required.",
        })

    return signals, findings
