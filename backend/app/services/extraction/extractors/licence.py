import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def extract_licence_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from Industry Licence (e.g. FSSAI Food Licence or Carrier Permit).
    Fields: licence_number, entity_name, licence_type, validity_date.
    """
    fields: List[ExtractedFieldData] = []

    # 1. FSSAI 14-digit licence number or generic licence regex
    fssai_match = re.search(r"\b(1\d{13})\b", text)
    if fssai_match:
        fields.append(
            ExtractedFieldData(
                field_name="licence_number",
                extracted_value=fssai_match.group(1),
                normalized_value=fssai_match.group(1),
                confidence_score=0.98,
                page_number=page_number,
                evidence_text=text[max(0, fssai_match.start()-20):min(len(text), fssai_match.end()+20)],
                extraction_method="DETERMINISTIC_REGEX",
            )
        )
        fields.append(
            ExtractedFieldData(
                field_name="licence_type",
                extracted_value="FSSAI Food Safety Licence",
                normalized_value="FSSAI",
                confidence_score=0.95,
                page_number=page_number,
                evidence_text="Matched 14-digit FSSAI registration structure",
                extraction_method="DETERMINISTIC_REGEX",
            )
        )
    else:
        # Generic licence number
        lic_match = re.search(r"(?:licen[sc]e|permit|registration)\s*(?:no|number)?\s*[:\.\-]?\s*([A-Z0-9\/\-]{6,25})\b", text, re.IGNORECASE)
        if lic_match:
            fields.append(
                ExtractedFieldData(
                    field_name="licence_number",
                    extracted_value=lic_match.group(1),
                    normalized_value=lic_match.group(1).strip().upper(),
                    confidence_score=0.88,
                    page_number=page_number,
                    evidence_text=lic_match.group(0),
                    extraction_method="DETERMINISTIC_REGEX",
                )
            )

    # 2. Validity / Expiry Date
    exp_match = re.search(r"(?:valid\s*(?:upto|till|until|to)|expiry\s*date)\s*[:\.\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if exp_match:
        fields.append(
            ExtractedFieldData(
                field_name="validity_date",
                extracted_value=exp_match.group(1),
                normalized_value=exp_match.group(1).replace("-", "/"),
                confidence_score=0.92,
                page_number=page_number,
                evidence_text=exp_match.group(0),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    return fields
