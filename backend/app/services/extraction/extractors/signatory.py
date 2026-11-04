import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def extract_signatory_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from Board Resolution / Power of Attorney.
    Fields: authorised_person_name, resolution_date, authority_scope.
    """
    fields: List[ExtractedFieldData] = []

    # 1. Authorised person name: "Resolved that Mr./Ms. [Name] ..."
    auth_match = re.search(r"resolved\s+that\s+(?:mr\.|ms\.|shri|smt\.)?\s*([A-Za-z\s\.]+?)\s*(?:director|partner|be\s+and\s+is\s+hereby\s+authori[zs]ed|is\s+hereby\s+empowered)", text, re.IGNORECASE)
    if not auth_match:
        auth_match = re.search(r"authori[zs]e(?:d)?\s+(?:mr\.|ms\.|shri|smt\.)?\s*([A-Za-z\s\.]+?)\s*(?:to\s+sign|as\s+signatory)", text, re.IGNORECASE)

    if auth_match:
        person_name = auth_match.group(1).strip()
        fields.append(
            ExtractedFieldData(
                field_name="authorised_person_name",
                extracted_value=person_name,
                normalized_value=re.sub(r"[^a-zA-Z\s\.]", "", person_name).strip().title(),
                confidence_score=0.89,
                page_number=page_number,
                evidence_text=auth_match.group(0),
                extraction_method="OCR_LAYOUT",
            )
        )

    # 2. Resolution Date
    res_date_match = re.search(r"(?:meeting\s+held\s+on|dated|resolution\s+passed\s+on)\s*[:\.\-]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if res_date_match:
        raw_dt = res_date_match.group(1)
        fields.append(
            ExtractedFieldData(
                field_name="resolution_date",
                extracted_value=raw_dt,
                normalized_value=raw_dt,
                confidence_score=0.91,
                page_number=page_number,
                evidence_text=res_date_match.group(0),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    return fields
