import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.application import Application, ConstitutionEnum
from app.models.document import Document, DocumentTypeEnum


def parse_categories(categories_json: Optional[str]) -> List[str]:
    """Parse categories from JSON string or return empty list."""
    if not categories_json:
        return []
    try:
        data = json.loads(categories_json)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def evaluate_checklist_rules(application: Application) -> List[Dict[str, Any]]:
    """
    Evaluates dynamic document checklist requirements based on:
    1. Legal constitution (Proprietorship, Partnership, LLP, Company)
    2. GST registration status
    3. Udyam MSME registration status
    4. Business activity classifications
    5. Buyer-specific policy
    """
    rules: List[Dict[str, Any]] = []
    constitution = (application.constitution or ConstitutionEnum.PROPRIETORSHIP.value).upper()
    categories = parse_categories(application.categories_json)

    # 1. PAN Proof
    if constitution == ConstitutionEnum.PROPRIETORSHIP.value:
        pan_title = "Proprietor's PAN Card"
        pan_desc = "Clear scanned copy of the individual proprietor's PAN card."
        pan_reason = "Mandatory for proprietorship identity verification as per Income Tax rules."
    else:
        pan_title = f"{constitution.replace('_', ' ').title()} Entity PAN Card"
        pan_desc = "Clear copy of the entity's permanent account number (PAN) card."
        pan_reason = "Mandatory legal entity identifier proof."

    rules.append({
        "document_type": DocumentTypeEnum.PAN_PROOF.value,
        "title": pan_title,
        "description": pan_desc,
        "is_required": True,
        "condition_explanation": pan_reason,
        "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
        "max_size_mb": 15,
    })

    # 2. Constitution Proof
    if constitution == ConstitutionEnum.PROPRIETORSHIP.value:
        const_title = "Proprietorship Establishment Proof"
        const_desc = "Shop & Establishment Certificate, Trade Licence, Udyam certificate, or local municipal registration."
        const_reason = "Proof of business existence for sole proprietorship."
    elif constitution == ConstitutionEnum.PARTNERSHIP.value:
        const_title = "Partnership Deed & Registration"
        const_desc = "Executed partnership deed and firm registration certificate (where registered)."
        const_reason = "Mandatory constitution instrument establishing the partnership."
    elif constitution == ConstitutionEnum.LLP.value:
        const_title = "LLP Agreement & Incorporation Certificate"
        const_desc = "Certificate of Incorporation issued by MCA and executed LLP Agreement."
        const_reason = "Statutory MCA incorporation proof for Limited Liability Partnership."
    elif constitution in [ConstitutionEnum.PVT_LTD.value, ConstitutionEnum.PUB_LTD.value]:
        const_title = "Certificate of Incorporation & MOA/AOA"
        const_desc = "MCA Certificate of Incorporation (with CIN) and Memorandum/Articles of Association."
        const_reason = "Statutory corporate identity proof under the Companies Act."
    else:
        const_title = "Business Constitution Document"
        const_desc = "Official government or statutory registration certificate."
        const_reason = "Entity registration proof."

    rules.append({
        "document_type": DocumentTypeEnum.CONSTITUTION_PROOF.value,
        "title": const_title,
        "description": const_desc,
        "is_required": True,
        "condition_explanation": const_reason,
        "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
        "max_size_mb": 15,
    })

    # 3. Bank Proof (Mandatory for all vendors)
    rules.append({
        "document_type": DocumentTypeEnum.BANK_PROOF.value,
        "title": "Bank Account Proof",
        "description": "Original cancelled cheque, first page of bank passbook, or bank account confirmation letter showing account number, beneficiary name, and IFSC.",
        "is_required": True,
        "condition_explanation": "Required to verify beneficiary account ownership and routing for payment disbursement.",
        "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
        "max_size_mb": 15,
    })

    # 4. GST Registration Certificate (Conditional on is_gst_registered)
    if application.is_gst_registered:
        rules.append({
            "document_type": DocumentTypeEnum.GST_CERTIFICATE.value,
            "title": "GST Registration Certificate (Form REG-06)",
            "description": "Complete 3-page GST certificate including Annexure A and Annexure B.",
            "is_required": True,
            "condition_explanation": "Mandatory since vendor declared active GST registration.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })
    else:
        rules.append({
            "document_type": DocumentTypeEnum.GST_CERTIFICATE.value,
            "title": "GST Registration Certificate",
            "description": "Not required (Vendor indicated non-GST registered status).",
            "is_required": False,
            "condition_explanation": "Not required for unregistered vendors under applicable turnover threshold.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })

    # 5. Udyam MSME Certificate (Conditional on is_udyam_registered)
    if application.is_udyam_registered:
        rules.append({
            "document_type": DocumentTypeEnum.UDYAM_CERTIFICATE.value,
            "title": "Udyam MSME Certificate",
            "description": "Permanent Udyam Registration Certificate issued by the Ministry of MSME with QR code.",
            "is_required": True,
            "condition_explanation": "Mandatory since vendor claimed MSME status under MSMED Act.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })
    else:
        rules.append({
            "document_type": DocumentTypeEnum.UDYAM_CERTIFICATE.value,
            "title": "Udyam MSME Certificate",
            "description": "Not required (MSME status not claimed).",
            "is_required": False,
            "condition_explanation": "Optional / Not applicable for non-MSME entities.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })

    # 6. Authorised Signatory Proof
    if constitution != ConstitutionEnum.PROPRIETORSHIP.value:
        rules.append({
            "document_type": DocumentTypeEnum.SIGNATORY_PROOF.value,
            "title": "Board Resolution / Letter of Authority",
            "description": "Extract of board resolution or power of attorney authorizing the signatory to enter contracts.",
            "is_required": True,
            "condition_explanation": f"Mandatory for {constitution.replace('_', ' ').title()} to establish signing authority.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })
    else:
        rules.append({
            "document_type": DocumentTypeEnum.SIGNATORY_PROOF.value,
            "title": "Authorised Signatory Evidence",
            "description": "Optional for sole proprietorship where proprietor is direct signatory.",
            "is_required": False,
            "condition_explanation": "Proprietor has inherent signing authority for sole proprietorship.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })

    # 7. Industry Specific Licence
    if "food_catering" in categories:
        rules.append({
            "document_type": DocumentTypeEnum.INDUSTRY_LICENCE.value,
            "title": "FSSAI Food Safety Licence",
            "description": "Valid Food Safety and Standards Authority of India (FSSAI) licence/registration.",
            "is_required": True,
            "condition_explanation": "Mandatory for food, beverage, and catering vendors.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })
    elif "logistics" in categories:
        rules.append({
            "document_type": DocumentTypeEnum.INDUSTRY_LICENCE.value,
            "title": "Transport & Fleet Carrier Permit",
            "description": "Commercial vehicle transport permit or freight forwarding licence.",
            "is_required": True,
            "condition_explanation": "Mandatory for logistics, transport, and freight service providers.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })
    elif any(cat in categories for cat in ["manufacturer", "construction"]):
        rules.append({
            "document_type": DocumentTypeEnum.INDUSTRY_LICENCE.value,
            "title": "Factory / Labour / Pollution Consent",
            "description": "Factory licence, labour registration, or state pollution control board consent.",
            "is_required": False,
            "condition_explanation": "Conditional based on buyer audit policy for manufacturing/construction.",
            "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_size_mb": 15,
        })

    # 8. Buyer Specific Policy Document (Configurable Buyer Policy)
    rules.append({
        "document_type": DocumentTypeEnum.BUYER_SPECIFIC.value,
        "title": "Buyer Code of Conduct & Compliance Acknowledgement",
        "description": "Signed copy of the buyer organization's anti-bribery, ethics, and ESG compliance declaration.",
        "is_required": False,
        "condition_explanation": f"Buyer Onboarding Policy: Recommended compliance acknowledgement for {application.organization.name if application.organization else 'buyer'}.",
        "accepted_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
        "max_size_mb": 15,
    })

    return rules


def sync_application_documents(db: Session, application: Application) -> List[Document]:
    """
    Synchronizes the database `documents` table records for the application
    with the current dynamic checklist evaluation rules.
    Preserves existing files, versions, and upload statuses.
    """
    evaluated_rules = evaluate_checklist_rules(application)
    existing_docs = {doc.document_type: doc for doc in application.documents}

    for rule in evaluated_rules:
        doc_type = rule["document_type"]
        if doc_type in existing_docs:
            doc = existing_docs[doc_type]
            doc.title = rule["title"]
            doc.is_required = rule["is_required"]
            doc.requirement_reason = rule["condition_explanation"]
        else:
            new_doc = Document(
                application_id=application.id,
                organisation_id=application.organisation_id,
                document_type=doc_type,
                title=rule["title"],
                is_required=rule["is_required"],
                requirement_reason=rule["condition_explanation"],
                status="PENDING",
            )
            db.add(new_doc)

    db.commit()
    db.refresh(application)
    return application.documents
