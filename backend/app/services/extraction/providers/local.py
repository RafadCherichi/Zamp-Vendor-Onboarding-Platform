from typing import List
from app.services.extraction.models import ExtractedFieldData
from app.services.extraction.providers.base import BaseExtractionProvider
from app.services.extraction.extractors import EXTRACTOR_REGISTRY


class LocalDeterministicProvider(BaseExtractionProvider):
    """
    Standard offline extraction provider relying on deterministic regular expressions,
    statutory Indian identifier rules, and OCR text layout heuristics.
    """

    @property
    def provider_name(self) -> str:
        return "LOCAL_DETERMINISTIC"

    def extract(self, text: str, document_type: str, page_number: int = 1) -> List[ExtractedFieldData]:
        extractor_fn = EXTRACTOR_REGISTRY.get(document_type)
        if extractor_fn:
            return extractor_fn(text, page_number)
        return []
