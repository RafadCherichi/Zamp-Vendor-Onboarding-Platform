import re
from typing import List, Optional
from app.services.extraction.models import ExtractedFieldData

KNOWN_BANKS = [
    "HDFC BANK", "ICICI BANK", "STATE BANK OF INDIA", "SBI", "AXIS BANK",
    "KOTAK MAHINDRA BANK", "PUNJAB NATIONAL BANK", "PNB", "BANK OF BARODA",
    "CANARA BANK", "UNION BANK OF INDIA", "INDUSIND BANK", "IDFC FIRST BANK",
    "YES BANK", "FEDERAL BANK", "STANDARD CHARTERED", "CITIBANK", "HSBC",
]


def extract_bank_fields(text: str, page_number: int = 1) -> List[ExtractedFieldData]:
    """
    Extracts structured fields from bank proof (cancelled cheque, bank statement, or passbook).
    Fields: bank_account_number, ifsc_code, account_holder_name, bank_name.
    """
    fields: List[ExtractedFieldData] = []
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 1. IFSC Code: 4 alphabets, 0, 6 alphanumeric
    ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text)
    if ifsc_match:
        raw_ifsc = ifsc_match.group(1).upper()
        start = max(0, ifsc_match.start() - 25)
        end = min(len(text), ifsc_match.end() + 25)
        fields.append(
            ExtractedFieldData(
                field_name="ifsc_code",
                extracted_value=ifsc_match.group(1),
                normalized_value=raw_ifsc,
                confidence_score=0.98,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 2. Bank Account Number: 9 to 18 digits (often near "A/c", "Account", or isolated on cheque)
    acc_match = re.search(r"(?:a/c|acc|account|ac)\s*(?:no|number)?\s*[:\.\-]?\s*(\d{9,18})\b", text, re.IGNORECASE)
    if not acc_match:
        # Fallback to standalone 9-18 digit numbers that are not IFSC or phone numbers
        all_nums = re.finditer(r"\b(\d{9,18})\b", text)
        for m in all_nums:
            num = m.group(1)
            # Exclude Indian phone numbers starting with 6, 7, 8, 9 of length 10 if near "mobile" or "phone"
            if len(num) == 10 and num[0] in "6789":
                surround = text[max(0, m.start()-15):min(len(text), m.end()+15)].lower()
                if any(w in surround for w in ["phone", "mobile", "tel", "cell"]):
                    continue
            acc_match = m
            break

    if acc_match:
        acc_num = acc_match.group(1) if acc_match.groups() else acc_match.group(0)
        start = max(0, acc_match.start() - 25)
        end = min(len(text), acc_match.end() + 25)
        fields.append(
            ExtractedFieldData(
                field_name="bank_account_number",
                extracted_value=acc_num,
                normalized_value=acc_num.strip(),
                confidence_score=0.94,
                page_number=page_number,
                evidence_text=text[start:end].strip(),
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 3. Bank Name identification
    detected_bank = None
    for b in KNOWN_BANKS:
        if b in text.upper():
            detected_bank = b
            break

    if detected_bank:
        fields.append(
            ExtractedFieldData(
                field_name="bank_name",
                extracted_value=detected_bank,
                normalized_value=detected_bank.title(),
                confidence_score=0.92,
                page_number=page_number,
                evidence_text=f"Matched bank identifier '{detected_bank}'",
                extraction_method="DETERMINISTIC_REGEX",
            )
        )

    # 4. Account Holder Name
    holder_name = None
    holder_evidence = ""
    for idx, line in enumerate(lines):
        line_clean = line.lower()
        if any(kw in line_clean for kw in ["pay to", "in the name of", "account name", "beneficiary name", "holder name"]):
            parts = re.split(r"(?:pay to|account name|beneficiary name|holder name)\s*[:\-]?", line, flags=re.IGNORECASE)
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                holder_name = parts[1].strip()
                holder_evidence = line
                break
        elif "for " in line_clean or line_clean.startswith("for "):
            # Cheque bottom signatory line: "For Apex Components & Fasteners"
            holder_name = re.sub(r"^for\s+", "", line, flags=re.IGNORECASE).strip()
            holder_evidence = line
            break

    if holder_name:
        clean_holder = re.sub(r"[^a-zA-Z0-9\s\.\&\-]", "", holder_name).strip()
        fields.append(
            ExtractedFieldData(
                field_name="account_holder_name",
                extracted_value=holder_name,
                normalized_value=clean_holder,
                confidence_score=0.86,
                page_number=page_number,
                evidence_text=holder_evidence,
                extraction_method="OCR_LAYOUT",
            )
        )

    return fields
