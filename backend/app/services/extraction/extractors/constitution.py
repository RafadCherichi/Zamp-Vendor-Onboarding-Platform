import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def extract_constitution_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from Constitution Proof (Certificate of Incorporation, MOA/AOA, Shop & Est).
    Fields: cin_or_llpin, legal_name, date_of_incorporation, constitution_type.
    """
    fields: List[ExtractedFieldData] = []
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 1. Corporate Identity Number (CIN): U or L + 5 digits + 2 state letters + 4 year digits + 3 letters + 6 digits
    cin_match = re.search(r"\b([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b", text)
    if not cin_match:
        # Check for LLPIN: AAA-1234
        cin_match = re.search(r"\b([A-Z]{3}-\d{4})\b", text)

    if cin_match:
        raw_cin = cin_match.group(1).upper()
        start = max(0, cin_match.start() - 25)
        end = min(len(text), cin_match.end() + 25)
        fields.append(
            ExtractedFieldData(
                field_name="cin_or_llpin",
                extracted_value=cin_match.group(1),
                normalized_value=raw_cin,
                confidence_score=0.98,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 2. Date of Incorporation / Registration
    date_match = re.search(r"(?:incorporated|established|registered)\s*(?:on|date)?\s*[:\.\-]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4}|\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if date_match:
        dt_raw = date_match.group(1)
        fields.append(
            ExtractedFieldData(
                field_name="date_of_incorporation",
                extracted_value=dt_raw,
                normalized_value=dt_raw,
                confidence_score=0.91,
                page_number=page_number,
                evidence_text=date_match.group(0),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 3. Company / Entity Legal Name
    comp_match = re.search(r"hereby\s+certif(?:y|ies)\s+that\s+([A-Za-z0-9\s\.\,\(\)\-]+?)\s+(?:is\s+incorporated|is\s+this\s+day)", text, re.IGNORECASE)
    if not comp_match:
        comp_match = re.search(r"name\s*of\s*(?:the\s*)?company\s*[:\-]?\s*([A-Za-z0-9\s\.\,\(\)\-]+)", text, re.IGNORECASE)

    if comp_match:
        extracted_name = comp_match.group(1).strip()
        clean_name = re.sub(r"[\r\n\t]+", " ", extracted_name).strip()
        fields.append(
            ExtractedFieldData(
                field_name="legal_name",
                extracted_value=extracted_name,
                normalized_value=clean_name,
                confidence_score=0.90,
                page_number=page_number,
                evidence_text=comp_match.group(0),
                extraction_method="OCR_LAYOUT",
            )
        )

    # 4. Constitution Type
    if "private limited" in text.lower():
        fields.append(
            ExtractedFieldData(
                field_name="constitution_type",
                extracted_value="Private Limited Company",
                normalized_value="PVT_LTD",
                confidence_score=0.95,
                page_number=page_number,
                evidence_text="Matched 'private limited' in text",
                extraction_method="DETERMINISTIC_REGEX",
            )
        )
    elif "limited liability partnership" in text.lower() or "llp" in text.lower():
        fields.append(
            ExtractedFieldData(
                field_name="constitution_type",
                extracted_value="Limited Liability Partnership",
                normalized_value="LLP",
                confidence_score=0.92,
                page_number=page_number,
                evidence_text="Matched 'limited liability partnership' in text",
                extraction_method="DETERMINISTIC_REGEX",
            )
        )
    elif "proprietorship" in text.lower() or "shop and establishment" in text.lower():
        fields.append(
            ExtractedFieldData(
                field_name="constitution_type",
                extracted_value="Sole Proprietorship",
                normalized_value="PROPRIETORSHIP",
                confidence_score=0.88,
                page_number=page_number,
                evidence_text="Matched establishment / proprietorship evidence",
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    return fields
