"""Storage-related FastAPI dependencies."""

from __future__ import annotations

from app.services.storage.file_storage import FileStorageService


def get_storage_service() -> FileStorageService:
    """Provide the file storage service (local backend by default)."""
    return FileStorageService()
