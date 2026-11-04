import re
from typing import List, Dict, Any, Optional
from app.models.application import Application
from app.models.validation import ValidationFinding, ValidationStatusEnum, ValidationSeverityEnum, ValidationLayerEnum
from app.services.validation.checksums import (
    validate_pan_structure,
    validate_gstin_structure,
    validate_cin_llpin_structure,
    validate_ifsc_structure,
    validate_udyam_structure,
    validate_indian_mobile,
    validate_indian_pincode,
)
from app.services.verification.simulated import mask_id


def run_layer_a_checks(app: Application) -> List[Dict[str, Any]]:
    """
    Executes Layer A deterministic input and identifier validation checks
    against application data. Returns a list of finding dicts ready to be instantiated.
    """
    findings: List[Dict[str, Any]] = []

    # 1. PAN Format and Constitution Check
    pan_val = (app.pan or "").strip().upper()
    if not pan_val:
        findings.append({
            "check_id": "A_PAN_FORMAT_AND_CONSTITUTION",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "PAN Structure and Constitution Alignment",
            "status": ValidationStatusEnum.FAILED.value,
            "severity": ValidationSeverityEnum.CRITICAL.value,
            "submitted_value": None,
            "extracted_value": None,
            "external_value": None,
            "evidence": "Business Identity Section: PAN is empty.",
            "explanation": "Permanent Account Number (PAN) is missing. PAN is mandatory for all Indian business entities.",
            "recommended_action": "Provide a valid 10-character PAN registered with the Income Tax Department.",
        })
    else:
        is_valid_pan, pan_err = validate_pan_structure(pan_val, app.constitution)
        if is_valid_pan:
            fourth_char = pan_val[3]
            findings.append({
                "check_id": "A_PAN_FORMAT_AND_CONSTITUTION",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "PAN Structure and Constitution Alignment",
                "status": ValidationStatusEnum.PASSED.value,
                "severity": ValidationSeverityEnum.CRITICAL.value,
                "submitted_value": mask_id(pan_val),
                "extracted_value": None,
                "external_value": None,
                "evidence": f"PAN {mask_id(pan_val)}: 4th char is '{fourth_char}' for constitution '{app.constitution}'.",
                "explanation": f"PAN format is structurally valid. The 4th character '{fourth_char}' correctly matches the declared legal constitution ({app.constitution}).",
                "recommended_action": "No action required.",
            })
        else:
            findings.append({
                "check_id": "A_PAN_FORMAT_AND_CONSTITUTION",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "PAN Structure and Constitution Alignment",
                "status": ValidationStatusEnum.FAILED.value,
                "severity": ValidationSeverityEnum.CRITICAL.value,
                "submitted_value": mask_id(pan_val),
                "extracted_value": None,
                "external_value": None,
                "evidence": f"PAN {mask_id(pan_val)}, Constitution: {app.constitution}. Error: {pan_err}",
                "explanation": f"PAN validation failed: {pan_err}",
                "recommended_action": "Correct the PAN to match the statutory entity constitution or update the selected business constitution.",
            })

    # 2. GSTIN Structure, State Code & Mod-36 Checksum
    if app.is_gst_registered:
        gstin_val = (app.gstin or "").strip().upper()
        if not gstin_val:
            findings.append({
                "check_id": "A_GSTIN_FORMAT_AND_CHECKSUM",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "GSTIN Structure, State Code & Mod-36 Checksum",
                "status": ValidationStatusEnum.FAILED.value,
                "severity": ValidationSeverityEnum.HIGH.value,
                "submitted_value": None,
                "extracted_value": None,
                "external_value": None,
                "evidence": "Vendor marked 'GST Registered' but provided no GSTIN.",
                "explanation": "GSTIN is missing while the business is declared as GST registered.",
                "recommended_action": "Provide a valid 15-character GSTIN or update registration status.",
            })
        else:
            is_valid_gst, gst_err = validate_gstin_structure(gstin_val)
            if is_valid_gst:
                state_code = gstin_val[:2]
                findings.append({
                    "check_id": "A_GSTIN_FORMAT_AND_CHECKSUM",
                    "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                    "check_name": "GSTIN Structure, State Code & Mod-36 Checksum",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.HIGH.value,
                    "submitted_value": mask_id(gstin_val),
                    "extracted_value": None,
                    "external_value": None,
                    "evidence": f"GSTIN {mask_id(gstin_val)}: state code {state_code}, valid 15-char structure and passing Mod-36 check digit.",
                    "explanation": f"GSTIN is structurally valid with verified state code '{state_code}' and passing Mod-36 checksum.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "A_GSTIN_FORMAT_AND_CHECKSUM",
                    "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                    "check_name": "GSTIN Structure, State Code & Mod-36 Checksum",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.HIGH.value,
                    "submitted_value": mask_id(gstin_val),
                    "extracted_value": None,
                    "external_value": None,
                    "evidence": f"GSTIN {mask_id(gstin_val)}. Error: {gst_err}",
                    "explanation": f"GSTIN validation failed: {gst_err}",
                    "recommended_action": "Review and enter the exact 15-digit statutory GSTIN as issued on the GST Registration Certificate.",
                })
    else:
        findings.append({
            "check_id": "A_GSTIN_FORMAT_AND_CHECKSUM",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "GSTIN Structure, State Code & Mod-36 Checksum",
            "status": ValidationStatusEnum.NOT_APPLICABLE.value,
            "severity": ValidationSeverityEnum.LOW.value,
            "submitted_value": "NOT_REGISTERED",
            "extracted_value": None,
            "external_value": None,
            "evidence": "Vendor marked exempt or unregistered for GST.",
            "explanation": "GST registration not declared for this vendor (turnover below threshold or exempt category).",
            "recommended_action": "Ensure GST exemption declaration is collected if applicable.",
        })

    # 3. CIN / LLPIN Check
    const_upper = (app.constitution or "").upper()
    if const_upper in ["PVT_LTD", "PUB_LTD", "LLP"]:
        cin_val = (app.cin_llpin or "").strip().upper()
        if not cin_val:
            findings.append({
                "check_id": "A_CIN_LLPIN_STRUCTURE",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "MCA CIN / LLPIN Registration Identifier",
                "status": ValidationStatusEnum.FAILED.value,
                "severity": ValidationSeverityEnum.HIGH.value,
                "submitted_value": None,
                "extracted_value": None,
                "external_value": None,
                "evidence": f"Constitution '{const_upper}' requires CIN/LLPIN but field is blank.",
                "explanation": f"Corporate entity ({const_upper}) must provide a valid MCA Corporate Identification Number (CIN) or LLP Identification Number (LLPIN).",
                "recommended_action": "Provide the 21-character CIN (for Companies) or 7-8 character LLPIN (for LLPs).",
            })
        else:
            is_valid_cin, cin_err = validate_cin_llpin_structure(cin_val, const_upper)
            if is_valid_cin:
                findings.append({
                    "check_id": "A_CIN_LLPIN_STRUCTURE",
                    "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                    "check_name": "MCA CIN / LLPIN Registration Identifier",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.HIGH.value,
                    "submitted_value": cin_val,
                    "extracted_value": None,
                    "external_value": None,
                    "evidence": f"Identifier {cin_val} matches statutory format for {const_upper}.",
                    "explanation": f"Registration identifier matches Ministry of Corporate Affairs (MCA) statutory format for {const_upper}.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "A_CIN_LLPIN_STRUCTURE",
                    "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                    "check_name": "MCA CIN / LLPIN Registration Identifier",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.HIGH.value,
                    "submitted_value": cin_val,
                    "extracted_value": None,
                    "external_value": None,
                    "evidence": f"Identifier {cin_val}. Error: {cin_err}",
                    "explanation": f"CIN/LLPIN validation failed: {cin_err}",
                    "recommended_action": "Provide the exact statutory MCA CIN or LLPIN as shown on the Certificate of Incorporation.",
                })
    else:
        findings.append({
            "check_id": "A_CIN_LLPIN_STRUCTURE",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "MCA CIN / LLPIN Registration Identifier",
            "status": ValidationStatusEnum.NOT_APPLICABLE.value,
            "severity": ValidationSeverityEnum.LOW.value,
            "submitted_value": "N/A",
            "extracted_value": None,
            "external_value": None,
            "evidence": f"Constitution '{const_upper}' does not require MCA incorporation.",
            "explanation": "Sole proprietorships and partnership firms do not possess an MCA CIN or LLPIN.",
            "recommended_action": "No action required.",
        })

    # 4. Bank IFSC Structure Check
    ifsc_val = (app.bank_ifsc or "").strip().upper()
    if not ifsc_val:
        findings.append({
            "check_id": "A_BANK_IFSC_STRUCTURE",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "Bank IFSC Code Format",
            "status": ValidationStatusEnum.FAILED.value,
            "severity": ValidationSeverityEnum.HIGH.value,
            "submitted_value": None,
            "extracted_value": None,
            "external_value": None,
            "evidence": "Bank IFSC is empty.",
            "explanation": "Bank IFSC is mandatory for electronic fund transfers (NEFT/RTGS).",
            "recommended_action": "Enter the 11-character IFSC code printed on the bank cheque or passbook.",
        })
    else:
        is_valid_ifsc, ifsc_err = validate_ifsc_structure(ifsc_val)
        if is_valid_ifsc:
            findings.append({
                "check_id": "A_BANK_IFSC_STRUCTURE",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "Bank IFSC Code Format",
                "status": ValidationStatusEnum.PASSED.value,
                "severity": ValidationSeverityEnum.HIGH.value,
                "submitted_value": ifsc_val,
                "extracted_value": None,
                "external_value": None,
                "evidence": f"IFSC {ifsc_val}: Bank code '{ifsc_val[:4]}', 5th character '0', branch '{ifsc_val[5:]}'.",
                "explanation": "IFSC code conforms to RBI statutory 11-character alphanumeric structure.",
                "recommended_action": "No action required.",
            })
        else:
            findings.append({
                "check_id": "A_BANK_IFSC_STRUCTURE",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "Bank IFSC Code Format",
                "status": ValidationStatusEnum.FAILED.value,
                "severity": ValidationSeverityEnum.HIGH.value,
                "submitted_value": ifsc_val,
                "extracted_value": None,
                "external_value": None,
                "evidence": f"IFSC {ifsc_val}. Error: {ifsc_err}",
                "explanation": f"IFSC validation failed: {ifsc_err}",
                "recommended_action": "Verify and provide a valid 11-character RBI IFSC code.",
            })

    # 5. Udyam Registration Check
    if app.is_udyam_registered:
        udyam_val = (app.udyam_number or "").strip().upper()
        if not udyam_val:
            findings.append({
                "check_id": "A_UDYAM_FORMAT",
                "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                "check_name": "MSME Udyam Registration Format",
                "status": ValidationStatusEnum.FAILED.value,
                "severity": ValidationSeverityEnum.MEDIUM.value,
                "submitted_value": None,
                "extracted_value": None,
                "external_value": None,
                "evidence": "Vendor marked 'MSME/Udyam Registered' but provided no Udyam number.",
                "explanation": "MSME Udyam registration number is missing.",
                "recommended_action": "Provide the Udyam number in format 'UDYAM-XX-00-0000000'.",
            })
        else:
            is_valid_udyam, udyam_err = validate_udyam_structure(udyam_val)
            if is_valid_udyam:
                findings.append({
                    "check_id": "A_UDYAM_FORMAT",
                    "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                    "check_name": "MSME Udyam Registration Format",
                    "status": ValidationStatusEnum.PASSED.value,
                    "severity": ValidationSeverityEnum.MEDIUM.value,
                    "submitted_value": udyam_val,
                    "extracted_value": None,
                    "external_value": None,
                    "evidence": f"Udyam number {udyam_val} matches statutory format.",
                    "explanation": "Udyam registration number strictly adheres to Ministry of MSME statutory format.",
                    "recommended_action": "No action required.",
                })
            else:
                findings.append({
                    "check_id": "A_UDYAM_FORMAT",
                    "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
                    "check_name": "MSME Udyam Registration Format",
                    "status": ValidationStatusEnum.FAILED.value,
                    "severity": ValidationSeverityEnum.MEDIUM.value,
                    "submitted_value": udyam_val,
                    "extracted_value": None,
                    "external_value": None,
                    "evidence": f"Udyam number {udyam_val}. Error: {udyam_err}",
                    "explanation": f"Udyam validation failed: {udyam_err}",
                    "recommended_action": "Provide the exact format 'UDYAM-XX-00-0000000' as printed on the Udyam Registration Certificate.",
                })
    else:
        findings.append({
            "check_id": "A_UDYAM_FORMAT",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "MSME Udyam Registration Format",
            "status": ValidationStatusEnum.NOT_APPLICABLE.value,
            "severity": ValidationSeverityEnum.LOW.value,
            "submitted_value": "NOT_REGISTERED",
            "extracted_value": None,
            "external_value": None,
            "evidence": "Vendor did not claim MSME / Udyam registration status.",
            "explanation": "Vendor is not registered under MSME Development Act.",
            "recommended_action": "No action required.",
        })

    # 6. Contact Details (Mobile & Email)
    mobile_val = (app.contact_mobile or "").strip()
    is_valid_mob, mob_err = validate_indian_mobile(mobile_val)
    email_val = (app.contact_email or "").strip()
    email_pattern = r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
    is_valid_email = bool(re.match(email_pattern, email_val))

    if is_valid_mob and is_valid_email:
        findings.append({
            "check_id": "A_CONTACT_DETAILS",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "Contact Mobile and Email Format",
            "status": ValidationStatusEnum.PASSED.value,
            "severity": ValidationSeverityEnum.MEDIUM.value,
            "submitted_value": f"{mobile_val[:2]}****{mobile_val[-2:] if len(mobile_val) >= 4 else ''} | {email_val}",
            "extracted_value": None,
            "external_value": None,
            "evidence": f"Valid 10-digit Indian mobile and RFC-compliant email address.",
            "explanation": "Contact mobile number and primary email address are structurally valid.",
            "recommended_action": "No action required.",
        })
    else:
        reasons = []
        if not is_valid_mob:
            reasons.append(mob_err or "Invalid mobile number")
        if not is_valid_email:
            reasons.append(f"Invalid email address '{email_val}'")
        findings.append({
            "check_id": "A_CONTACT_DETAILS",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "Contact Mobile and Email Format",
            "status": ValidationStatusEnum.FAILED.value,
            "severity": ValidationSeverityEnum.MEDIUM.value,
            "submitted_value": f"{mobile_val} | {email_val}",
            "extracted_value": None,
            "external_value": None,
            "evidence": "; ".join(reasons),
            "explanation": f"Contact details validation failed: {'; '.join(reasons)}",
            "recommended_action": "Provide a valid 10-digit Indian mobile number and valid business email address.",
        })

    # 7. Registered Address PIN Code
    pin_val = (app.pincode or "").strip()
    is_valid_pin, pin_err = validate_indian_pincode(pin_val)
    if is_valid_pin:
        findings.append({
            "check_id": "A_PINCODE_FORMAT",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "Postal PIN Code Format",
            "status": ValidationStatusEnum.PASSED.value,
            "severity": ValidationSeverityEnum.LOW.value,
            "submitted_value": pin_val,
            "extracted_value": None,
            "external_value": None,
            "evidence": f"6-digit Indian PIN code {pin_val}.",
            "explanation": "Postal PIN code is a valid 6-digit Indian postal code.",
            "recommended_action": "No action required.",
        })
    else:
        findings.append({
            "check_id": "A_PINCODE_FORMAT",
            "layer": ValidationLayerEnum.LAYER_A_INPUT.value,
            "check_name": "Postal PIN Code Format",
            "status": ValidationStatusEnum.FAILED.value,
            "severity": ValidationSeverityEnum.LOW.value,
            "submitted_value": pin_val,
            "extracted_value": None,
            "external_value": None,
            "evidence": f"PIN code '{pin_val}': {pin_err}",
            "explanation": f"Postal PIN code validation failed: {pin_err}",
            "recommended_action": "Provide a valid 6-digit Indian postal PIN code.",
        })

    return findings
