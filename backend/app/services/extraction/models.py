from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ExtractedFieldData:
    field_name: str
    extracted_value: str
    normalized_value: Optional[str] = None
    confidence_score: float = 1.0
    page_number: int = 1
    evidence_text: Optional[str] = None
    bounding_box: Optional[List[List[float]]] = None
    extraction_method: str = "DETERMINISTIC_PARSER"


@dataclass
class DocumentExtractionOutput:
    detected_document_type: str
    classification_confidence: float
    classification_reason: str
    is_type_match: bool
    fields: List[ExtractedFieldData]
    raw_text: str
    page_count: int
    provider_used: str
    review_flags: List[str] = field(default_factory=list)
    status: str = "EXTRACTED"
