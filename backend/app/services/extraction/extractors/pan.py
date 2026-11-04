import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def extract_pan_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from an Indian PAN card.
    Fields: pan_number, name, dob_or_incorporation, father_name.
    """
    fields: List[ExtractedFieldData] = []
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 1. PAN Number regex: 5 uppercase letters, 4 digits, 1 uppercase letter
    pan_matches = re.finditer(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    found_pan = None
    for match in pan_matches:
        pan_val = match.group(1).upper()
        # Verify 4th character is valid constitution character (P, C, H, F, A, T, B, L, J, G)
        if pan_val[3] in "PCHFATBLJG":
            found_pan = pan_val
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            fields.append(
                ExtractedFieldData(
                    field_name="pan_number",
                    extracted_value=match.group(1),
                    normalized_value=pan_val,
                    confidence_score=0.98,
                    page_number=page_number,
                    evidence_text=text[start:end].strip(),
                    extraction_method="DETERMINISTIC_REGEX",
                )
            )
            break

    # 2. Date of Birth or Incorporation: DD/MM/YYYY or DD-MM-YYYY
    dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
    if dob_match:
        dob_raw = dob_match.group(1)
        dob_norm = dob_raw.replace("-", "/")
        start = max(0, dob_match.start() - 25)
        end = min(len(text), dob_match.end() + 25)
        fields.append(
            ExtractedFieldData(
                field_name="date_of_birth_or_incorporation",
                extracted_value=dob_raw,
                normalized_value=dob_norm,
                confidence_score=0.92,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 3. Name extraction heuristic
    # Often appears after "INCOME TAX DEPARTMENT" or explicitly labeled "Name:" or "Name"
    name_extracted = None
    evidence = ""
    for idx, line in enumerate(lines):
        line_clean = line.upper()
        if any(h in line_clean for h in ["NAME", "NAME /", "NAME:"]):
            # Check next line or inline
            parts = re.split(r"name\s*[:\-]?", line, flags=re.IGNORECASE)
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                name_extracted = parts[1].strip()
                evidence = line
                break
            elif idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 2 and not any(kw in lines[idx + 1].upper() for kw in ["FATHER", "DATE", "PERMANENT"]):
                name_extracted = lines[idx + 1].strip()
                evidence = f"{line}\n{lines[idx + 1]}"
                break

    if not name_extracted:
        # Fallback: look for lines with 2-4 uppercase words that do not contain keywords
        ignore_words = {"INCOME", "TAX", "DEPARTMENT", "GOVT", "INDIA", "GOVERNMENT", "PERMANENT", "ACCOUNT", "NUMBER", "CARD", "SIGNATURE"}
        for line in lines:
            words = [w for w in line.split() if w.isalpha()]
            if 2 <= len(words) <= 5 and not any(w.upper() in ignore_words for w in words):
                name_extracted = " ".join(words)
                evidence = line
                break

    if name_extracted:
        # Clean name
        clean_name = re.sub(r"[^a-zA-Z\s\.]", "", name_extracted).strip()
        fields.append(
            ExtractedFieldData(
                field_name="holder_name",
                extracted_value=name_extracted,
                normalized_value=clean_name.title(),
                confidence_score=0.88,
                page_number=page_number,
                evidence_text=evidence,
                extraction_method="OCR_LAYOUT",
            )
        )

    # 4. Father's Name (if individual)
    for idx, line in enumerate(lines):
        if "FATHER" in line.upper():
            parts = re.split(r"father(?:'s)?\s*name\s*[:\-]?", line, flags=re.IGNORECASE)
            f_name = None
            f_ev = line
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                f_name = parts[1].strip()
            elif idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 2 and not any(kw in lines[idx + 1].upper() for kw in ["DATE", "DOB", "SIGNATURE", "PERMANENT"]):
                f_name = lines[idx + 1].strip()
                f_ev = f"{line}\n{lines[idx + 1]}"

            if f_name:
                fields.append(
                    ExtractedFieldData(
                        field_name="father_name",
                        extracted_value=f_name,
                        normalized_value=re.sub(r"[^a-zA-Z\s\.]", "", f_name).strip().title(),
                        confidence_score=0.85,
                        page_number=page_number,
                        evidence_text=f_ev,
                        extraction_method="OCR_LAYOUT",
                    )
                )
            break

    return fields
