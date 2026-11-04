from abc import ABC, abstractmethod
from typing import List
from app.services.extraction.models import ExtractedFieldData


class BaseExtractionProvider(ABC):
    """
    Abstract interface for document field extraction providers.
    Enables pluggable AI and deterministic engines without altering domain services.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def extract(self, text: str, document_type: str, page_number: int = 1) -> List[ExtractedFieldData]:
        pass
