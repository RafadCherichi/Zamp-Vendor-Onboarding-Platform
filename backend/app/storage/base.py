from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Dict, Any


class StorageAdapter(ABC):
    """
    Abstract interface for private document object storage.
    Implementations handle secure upload, short-lived signed URL generation,
    retrieval, and deletion.
    """

    @abstractmethod
    def save_file(
        self,
        file_obj: BinaryIO,
        destination_path: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a file into private object storage.
        Returns the persistent storage key / path.
        """
        pass

    @abstractmethod
    def get_presigned_url(self, storage_key: str, expires_in_seconds: int = 300) -> str:
        """
        Generate a short-lived URL for secure private file viewing/download.
        Default expiry is 300 seconds (5 minutes).
        """
        pass

    @abstractmethod
    def file_exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage."""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from storage."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verify storage backend availability and read/write access."""
        pass
