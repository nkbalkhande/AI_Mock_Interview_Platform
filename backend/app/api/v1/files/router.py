"""Serve uploaded files from local storage.

Files are stored under ``settings.STORAGE_ROOT`` with random UUID-based names.
This endpoint resolves the storage-relative path and streams the file back.
Only files within the storage root are served (path-traversal is blocked).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies.storage import get_storage_service
from app.services.storage.file_storage import FileStorageService

router = APIRouter()


@router.get("/{file_path:path}")
async def serve_file(
    file_path: str,
    storage: FileStorageService = Depends(get_storage_service),
) -> FileResponse:
    resolved = storage.resolve(file_path)

    # Block path-traversal attempts.
    try:
        resolved.resolve().relative_to(storage._root.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found.")

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Not found.")

    return FileResponse(resolved)
