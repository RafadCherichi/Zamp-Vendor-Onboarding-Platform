import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def extract_gst_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from Form GST REG-06 Certificate.
    Fields: gstin, legal_name, trade_name, constitution_of_business, registration_date, principal_place_of_business.
    """
    fields: List[ExtractedFieldData] = []
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 1. GSTIN regex: 15 alphanumeric characters matching Indian GST format
    gstin_match = re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b", text)
    if gstin_match:
        raw_gstin = gstin_match.group(1).upper()
        start = max(0, gstin_match.start() - 30)
        end = min(len(text), gstin_match.end() + 30)
        fields.append(
            ExtractedFieldData(
                field_name="gstin",
                extracted_value=gstin_match.group(1),
                normalized_value=raw_gstin,
                confidence_score=0.99,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 2. Legal Name
    for idx, line in enumerate(lines):
        if re.search(r"legal\s*name", line, re.IGNORECASE):
            parts = re.split(r"legal\s*name\s*[:\-]?", line, flags=re.IGNORECASE)
            val = None
            evidence = line
            if len(parts) > 1 and len(parts[1].strip()) > 2:
                val = parts[1].strip()
            elif idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 2 and not any(kw in lines[idx + 1].lower() for kw in ["trade", "constitution", "address", "date"]):
                val = lines[idx + 1].strip()
                evidence = f"{line}\n{lines[idx + 1]}"

            if val:
                fields.append(
                    ExtractedFieldData(
                        field_name="legal_name",
                        extracted_value=val,
                        normalized_value=val.strip(),
                        confidence_score=0.92,
                        page_number=page_number,
                        evidence_text=evidence,
                        extraction_method="OCR_LAYOUT",
                    )
                )
            break

    # 3. Trade Name
    for idx, line in enumerate(lines):
        if re.search(r"trade\s*name", line, re.IGNORECASE):
            parts = re.split(r"trade\s*name\s*[:\-]?", line, flags=re.IGNORECASE)
            val = None
            evidence = line
            if len(parts) > 1 and len(parts[1].strip()) > 2:
                val = parts[1].strip()
            elif idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 2 and not any(kw in lines[idx + 1].lower() for kw in ["constitution", "address", "date", "period"]):
                val = lines[idx + 1].strip()
                evidence = f"{line}\n{lines[idx + 1]}"

            if val:
                fields.append(
                    ExtractedFieldData(
                        field_name="trade_name",
                        extracted_value=val,
                        normalized_value=val.strip(),
                        confidence_score=0.90,
                        page_number=page_number,
                        evidence_text=evidence,
                        extraction_method="OCR_LAYOUT",
                    )
                )
            break

    # 4. Constitution of Business
    for idx, line in enumerate(lines):
        if re.search(r"constitution\s*of\s*business", line, re.IGNORECASE):
            parts = re.split(r"constitution\s*of\s*business\s*[:\-]?", line, flags=re.IGNORECASE)
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
                        field_name="constitution_of_business",
                        extracted_value=val,
                        normalized_value=val.strip().title(),
                        confidence_score=0.88,
                        page_number=page_number,
                        evidence_text=evidence,
                        extraction_method="OCR_LAYOUT",
                    )
                )
            break

    # 5. Registration Date / Date of Liability
    date_match = re.search(r"(?:date\s*of\s*(?:liability|registration|validity|issue))\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if date_match:
        raw_dt = date_match.group(1)
        fields.append(
            ExtractedFieldData(
                field_name="registration_date",
                extracted_value=raw_dt,
                normalized_value=raw_dt.replace("-", "/"),
                confidence_score=0.90,
                page_number=page_number,
                evidence_text=date_match.group(0),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 6. Principal Place of Business
    for idx, line in enumerate(lines):
        if re.search(r"principal\s*place\s*of\s*business", line, re.IGNORECASE):
            # Gather next 1-3 lines as address
            addr_lines = []
            for j in range(idx + 1, min(len(lines), idx + 4)):
                if any(stop_kw in lines[j].lower() for stop_kw in ["date of", "type of registration", "annexure", "jurisdiction"]):
                    break
                addr_lines.append(lines[j])

            if addr_lines:
                full_addr = ", ".join(addr_lines)
                fields.append(
                    ExtractedFieldData(
                        field_name="principal_place_of_business",
                        extracted_value=full_addr,
                        normalized_value=full_addr,
                        confidence_score=0.84,
                        page_number=page_number,
                        evidence_text=f"{line}\n" + "\n".join(addr_lines),
                        extraction_method="OCR_LAYOUT",
                    )
                )
            break

    return fields
