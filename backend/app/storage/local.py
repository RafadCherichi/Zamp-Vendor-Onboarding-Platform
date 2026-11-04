import os
import shutil
from typing import Optional, BinaryIO, Dict, Any
from pathlib import Path
from app.storage.base import StorageAdapter
from app.config import settings


class LocalStorageAdapter(StorageAdapter):
    """
    Local filesystem implementation of private object storage for development and testing.
    Keeps files in an isolated directory outside of public web roots.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Prevent directory traversal attacks
        safe_key = os.path.normpath(storage_key).lstrip("\\/")
        resolved = (self.base_dir / safe_key).resolve()
        if not str(resolved).startswith(str(self.base_dir)):
            raise ValueError(f"Illegal path traversal attempt: {storage_key}")
        return resolved

    def save_file(
        self,
        file_obj: BinaryIO,
        destination_path: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        target_path = self._resolve_path(destination_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "wb") as f_out:
            shutil.copyfileobj(file_obj, f_out)

        # Normalised relative storage key
        return str(target_path.relative_to(self.base_dir)).replace("\\", "/")

    def get_presigned_url(self, storage_key: str, expires_in_seconds: int = 300) -> str:
        # For local development, construct local API endpoint for private file preview
        return f"{settings.API_V1_STR}/documents/preview?key={storage_key}&expires={expires_in_seconds}"

    def file_exists(self, storage_key: str) -> bool:
        try:
            return self._resolve_path(storage_key).is_file()
        except ValueError:
            return False

    def get_file(self, storage_key: str) -> Optional[BinaryIO]:
        try:
            path = self._resolve_path(storage_key)
            if path.is_file():
                return open(path, "rb")
            return None
        except ValueError:
            return None

    def get_file_bytes(self, storage_key: str) -> Optional[bytes]:
        try:
            path = self._resolve_path(storage_key)
            if path.is_file():
                with open(path, "rb") as f:
                    return f.read()
            return None
        except ValueError:
            return None

    def delete_file(self, storage_key: str) -> bool:
        try:
            path = self._resolve_path(storage_key)
            if path.is_file():
                path.unlink()
                return True
            return False
        except ValueError:
            return False

    def health_check(self) -> Dict[str, Any]:
        try:
            # Check write and read permission
            test_file = self.base_dir / ".storage_health_check"
            test_file.write_text("ok", encoding="utf-8")
            content = test_file.read_text(encoding="utf-8")
            test_file.unlink()
            if content == "ok":
                return {
                    "backend": "local",
                    "status": "ready",
                    "path_or_bucket": str(self.base_dir),
                }
            return {
                "backend": "local",
                "status": "error",
                "path_or_bucket": str(self.base_dir),
            }
        except Exception as exc:
            return {
                "backend": "local",
                "status": f"error: {str(exc)}",
                "path_or_bucket": str(self.base_dir),
            }


# Storage singleton factory
def get_storage_adapter() -> StorageAdapter:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageAdapter()
    # Supabase or S3 adapters can be plugged in when credentials are provided
    return LocalStorageAdapter()
