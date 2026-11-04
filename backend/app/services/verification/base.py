from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class VerificationResult:
    verification_type: str
    provider_name: str
    request_id: str
    submitted_identifier: str
    status: VerificationStatus
    is_simulated: bool
    returned_attributes: Dict[str, Any]
    reason: str
    duration_ms: int


class BaseVerificationAdapter(ABC):
    """
    Abstract interface for authoritative government and banking verification providers.
    Supports future transition to live API integrations while enforcing standard schemas.
    """

    @property
    @abstractmethod
    def verification_type(self) -> str:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def verify(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        pass
