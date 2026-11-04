import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from app.models.document import DocumentTypeEnum


@dataclass
class ClassificationAlternative:
    document_type: str
    confidence: float


@dataclass
class DocumentClassificationResult:
    predicted_type: str
    confidence: float
    reason: str
    is_type_match: bool
    alternatives: List[ClassificationAlternative] = field(default_factory=list)


# Classification rule definitions: keywords, weights, and signature patterns
CLASSIFICATION_SIGNATURES: Dict[str, Dict[str, Any]] = {
    DocumentTypeEnum.PAN_PROOF.value: {
        "keywords": [
            ("income tax department", 30),
            ("permanent account number", 30),
            ("govt. of india", 15),
            ("government of india", 15),
            ("father's name", 15),
            ("date of birth", 15),
            ("pan card", 20),
        ],
        "regex_patterns": [
            (r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 40),  # Valid Indian PAN format
        ],
    },
    DocumentTypeEnum.GST_CERTIFICATE.value: {
        "keywords": [
            ("form gst reg-06", 45),
            ("registration certificate", 20),
            ("goods and services tax", 30),
            ("central goods and services tax", 20),
            ("principal place of business", 25),
            ("date of liability", 20),
            ("annexure a", 15),
            ("annexure b", 15),
            ("gstin", 25),
        ],
        "regex_patterns": [
            (r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b", 40),  # GSTIN
        ],
    },
    DocumentTypeEnum.BANK_PROOF.value: {
        "keywords": [
            ("cancelled", 30),
            ("cheque", 30),
            ("account number", 25),
            ("a/c no", 20),
            ("ifsc", 30),
            ("rtgs", 15),
            ("neft", 15),
            ("savings a/c", 15),
            ("current a/c", 15),
            ("branch", 10),
            ("bank statement", 25),
            ("passbook", 25),
        ],
        "regex_patterns": [
            (r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 35),  # IFSC code pattern
        ],
    },
    DocumentTypeEnum.UDYAM_CERTIFICATE.value: {
        "keywords": [
            ("udyam registration certificate", 45),
            ("ministry of micro, small", 30),
            ("medium enterprises", 25),
            ("udyam", 25),
            ("msme", 25),
            ("national industry classification", 20),
            ("date of incorporation", 15),
            ("enterprise type", 20),
        ],
        "regex_patterns": [
            (r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", 45),  # Standard Udyam format
        ],
    },
    DocumentTypeEnum.CONSTITUTION_PROOF.value: {
        "keywords": [
            ("certificate of incorporation", 40),
            ("memorandum of association", 35),
            ("articles of association", 35),
            ("ministry of corporate affairs", 30),
            ("registrar of companies", 30),
            ("companies act", 25),
            ("shop and establishment", 40),
            ("partnership deed", 40),
            ("limited liability partnership", 30),
            ("llp agreement", 35),
        ],
        "regex_patterns": [
            (r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", 40),  # CIN number
            (r"\b[A-Z]{3}-\d{4}\b", 25),  # LLPIN
        ],
    },
    DocumentTypeEnum.SIGNATORY_PROOF.value: {
        "keywords": [
            ("board resolution", 40),
            ("certified true copy", 30),
            ("extract of the minutes", 35),
            ("power of attorney", 40),
            ("authorised signatory", 30),
            ("resolved that", 35),
            ("board of directors", 25),
            ("sign and execute", 20),
        ],
        "regex_patterns": [],
    },
    DocumentTypeEnum.INDUSTRY_LICENCE.value: {
        "keywords": [
            ("food safety and standards authority", 45),
            ("fssai", 40),
            ("licence under fss act", 40),
            ("carriage permit", 35),
            ("motor vehicles act", 30),
            ("transport commissioner", 30),
            ("pollution control board", 35),
            ("consent to operate", 30),
            ("factory licence", 35),
        ],
        "regex_patterns": [
            (r"\b1\d{13}\b", 30),  # 14-digit FSSAI number
        ],
    },
    DocumentTypeEnum.BUYER_SPECIFIC.value: {
        "keywords": [
            ("code of conduct", 40),
            ("code of ethics", 35),
            ("non-disclosure agreement", 35),
            ("anti-bribery", 35),
            ("esg declaration", 30),
            ("vendor compliance declaration", 35),
        ],
        "regex_patterns": [],
    },
}


def classify_document(full_text: str, target_document_type: str) -> DocumentClassificationResult:
    """
    Classifies the document content into a known DocumentTypeEnum based on text patterns,
    keywords, and official Indian government format identifiers.
    """
    if not full_text or len(full_text.strip()) < 10:
        return DocumentClassificationResult(
            predicted_type="UNKNOWN",
            confidence=0.0,
            reason="Unreadable document: Insufficient text extracted to determine document type.",
            is_type_match=False,
            alternatives=[],
        )

    text_lower = full_text.lower()
    scores: Dict[str, float] = {doc_type: 0.0 for doc_type in CLASSIFICATION_SIGNATURES}
    evidence_notes: Dict[str, List[str]] = {doc_type: [] for doc_type in CLASSIFICATION_SIGNATURES}

    for doc_type, signature in CLASSIFICATION_SIGNATURES.items():
        # 1. Keyword matching
        for kw, weight in signature["keywords"]:
            if kw in text_lower:
                scores[doc_type] += weight
                evidence_notes[doc_type].append(f"found phrase '{kw}'")

        # 2. Regex pattern matching
        for pattern, weight in signature["regex_patterns"]:
            matches = re.findall(pattern, full_text, flags=re.IGNORECASE)
            if matches:
                scores[doc_type] += weight
                sample = matches[0] if len(matches) == 1 else f"{matches[0]} (+{len(matches)-1})"
                evidence_notes[doc_type].append(f"matched pattern '{sample}'")

    # Sort candidates by score descending
    sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_type, top_score = sorted_candidates[0]

    # Normalize confidence to 0.0 - 1.0 (threshold score ~ 70 for 0.90+)
    if top_score <= 0:
        return DocumentClassificationResult(
            predicted_type="UNKNOWN",
            confidence=0.1,
            reason="No known document headers, identifier formats, or statutory markers detected.",
            is_type_match=False,
            alternatives=[],
        )

    # Base confidence calculation
    confidence = min(0.99, round(top_score / 85.0, 2))
    confidence = max(0.20, confidence)

    # Compile alternatives
    alternatives = [
        ClassificationAlternative(
            document_type=c_type,
            confidence=min(0.95, round(c_score / 85.0, 2)),
        )
        for c_type, c_score in sorted_candidates[1:3]
        if c_score >= 20
    ]

    matched_reasons = evidence_notes.get(top_type, [])
    reason_str = f"Classified as {top_type.replace('_', ' ').title()}: " + ", ".join(matched_reasons[:3])

    is_match = (top_type == target_document_type)

    if not is_match:
        reason_str += f". Note: Uploaded to '{target_document_type}' slot but content strongly matches '{top_type}'."

    return DocumentClassificationResult(
        predicted_type=top_type,
        confidence=confidence,
        reason=reason_str,
        is_type_match=is_match,
        alternatives=alternatives,
    )
