import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def extract_udyam_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from Udyam MSME Certificate.
    Fields: udyam_number, enterprise_name, enterprise_type, major_activity.
    """
    fields: List[ExtractedFieldData] = []
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 1. Udyam Registration Number: UDYAM-XX-00-0000000
    udyam_match = re.search(r"\b(UDYAM-[A-Z]{2}-\d{2}-\d{7})\b", text, re.IGNORECASE)
    if udyam_match:
        raw_val = udyam_match.group(1).upper()
        start = max(0, udyam_match.start() - 25)
        end = min(len(text), udyam_match.end() + 25)
        fields.append(
            ExtractedFieldData(
                field_name="udyam_registration_number",
                extracted_value=udyam_match.group(1),
                normalized_value=raw_val,
                confidence_score=0.99,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 2. Enterprise Name
    for idx, line in enumerate(lines):
        if re.search(r"name\s*of\s*enterprise", line, re.IGNORECASE):
            parts = re.split(r"name\s*of\s*enterprise\s*[:\-]?", line, flags=re.IGNORECASE)
            val = None
            evidence = line
            if len(parts) > 1 and len(parts[1].strip()) > 2:
                val = parts[1].strip()
            elif idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 2:
                val = lines[idx + 1].strip()
                evidence = f"{line}\n{lines[idx + 1]}"

            if val:
                fields.append(
                    ExtractedFieldData(
                        field_name="enterprise_name",
                        extracted_value=val,
                        normalized_value=val.strip(),
                        confidence_score=0.92,
                        page_number=page_number,
                        evidence_text=evidence,
                        extraction_method="OCR_LAYOUT",
                    )
                )
            break

    # 3. Enterprise Type / Classification (Micro / Small / Medium)
    type_match = re.search(r"\b(MICRO|SMALL|MEDIUM)\b", text, re.IGNORECASE)
    if type_match:
        ent_type = type_match.group(1).upper()
        start = max(0, type_match.start() - 20)
        end = min(len(text), type_match.end() + 20)
        fields.append(
            ExtractedFieldData(
                field_name="enterprise_type",
                extracted_value=type_match.group(1),
                normalized_value=ent_type,
                confidence_score=0.90,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 4. Major Activity: Services or Manufacturing
    act_match = re.search(r"\b(MANUFACTURING|SERVICES)\b", text, re.IGNORECASE)
    if act_match:
        act_val = act_match.group(1).upper()
        fields.append(
            ExtractedFieldData(
                field_name="major_activity",
                extracted_value=act_match.group(1),
                normalized_value=act_val,
                confidence_score=0.88,
                page_number=page_number,
                evidence_text=act_match.group(0),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    return fields
