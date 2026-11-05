import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData


def is_valid_name_candidate(text_val: str) -> bool:
    """Checks whether a string is a credible human or business entity name."""
    if not text_val:
        return False
    # If it contains date patterns or pure digits, it's not a name
    if re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text_val) or re.search(r"\b\d{6,8}\b", text_val):
        return False
    # Must contain at least 2 alphabetic characters
    alpha_count = sum(1 for c in text_val if c.isalpha())
    if alpha_count < 2:
        return False
    # Must not be pure numbers or punctuation
    clean = re.sub(r"[^a-zA-Z\s\.]", "", text_val).strip()
    if len(clean) < 2:
        return False
    # Disallow common document header keywords
    header_keywords = {
        "INCOME", "TAX", "DEPARTMENT", "GOVT", "INDIA", "GOVERNMENT", "OF",
        "PERMANENT", "ACCOUNT", "NUMBER", "CARD", "SIGNATURE", "DATE",
        "BIRTH", "INCORPORATION", "FATHER", "NAME", "DOB", "PHOTO"
    }
    words = clean.upper().split()
    if all(w in header_keywords for w in words):
        return False
    return True


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
    is_individual = True
    for match in pan_matches:
        pan_val = match.group(1).upper()
        # Verify 4th character is valid constitution character (P, C, H, F, A, T, B, L, J, G)
        if pan_val[3] in "PCHFATBLJG":
            found_pan = pan_val
            is_individual = (pan_val[3] == "P")
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
    name_extracted = None
    evidence = ""
    for idx, line in enumerate(lines):
        line_clean = line.upper()
        if any(h in line_clean for h in ["NAME", "NAME /", "NAME:"]) and not any(h in line_clean for h in ["FATHER", "MOTHER"]):
            parts = re.split(r"name\s*[:\-]?", line, flags=re.IGNORECASE)
            if len(parts) > 1 and is_valid_name_candidate(parts[1].strip()):
                name_extracted = parts[1].strip()
                evidence = line
                break
            elif idx + 1 < len(lines) and is_valid_name_candidate(lines[idx + 1].strip()):
                name_extracted = lines[idx + 1].strip()
                evidence = f"{line}\n{lines[idx + 1]}"
                break

    if not name_extracted:
        # Fallback: look for lines with 2-5 words that are valid name candidates
        for line in lines:
            if is_valid_name_candidate(line):
                name_extracted = line
                evidence = line
                break

    if name_extracted and is_valid_name_candidate(name_extracted):
        clean_name = re.sub(r"[^a-zA-Z\s\.]", "", name_extracted).strip().title()
        if len(clean_name) >= 2:
            fields.append(
                ExtractedFieldData(
                    field_name="holder_name",
                    extracted_value=name_extracted,
                    normalized_value=clean_name,
                    confidence_score=0.88,
                    page_number=page_number,
                    evidence_text=evidence,
                    extraction_method="OCR_LAYOUT",
                )
            )

    # 4. Father's Name (only for individuals with 4th char 'P')
    if is_individual:
        for idx, line in enumerate(lines):
            if "FATHER" in line.upper():
                parts = re.split(r"father(?:'s)?\s*name\s*[:\-]?", line, flags=re.IGNORECASE)
                f_name = None
                f_ev = line
                if len(parts) > 1 and is_valid_name_candidate(parts[1].strip()):
                    f_name = parts[1].strip()
                elif idx + 1 < len(lines) and is_valid_name_candidate(lines[idx + 1].strip()):
                    f_name = lines[idx + 1].strip()
                    f_ev = f"{line}\n{lines[idx + 1]}"
                elif idx + 2 < len(lines) and is_valid_name_candidate(lines[idx + 2].strip()):
                    # In case an empty line or layout gap exists
                    f_name = lines[idx + 2].strip()
                    f_ev = f"{line}\n{lines[idx + 2]}"

                if f_name and is_valid_name_candidate(f_name):
                    clean_f_name = re.sub(r"[^a-zA-Z\s\.]", "", f_name).strip().title()
                    if len(clean_f_name) >= 2:
                        fields.append(
                            ExtractedFieldData(
                                field_name="father_name",
                                extracted_value=f_name,
                                normalized_value=clean_f_name,
                                confidence_score=0.85,
                                page_number=page_number,
                                evidence_text=f_ev,
                                extraction_method="OCR_LAYOUT",
                            )
                        )
                break

    return fields
