"""Application-wide constant values.

Domain enumerations (interview status, roles, etc.) live in
``app.domain.enums``. Tunable numbers live in ``settings/config.yaml``
and are re-exported here so existing imports keep working.
"""

from __future__ import annotations

from app.core.config import settings

# Pagination
DEFAULT_PAGE_SIZE = settings.app.default_page_size
MAX_PAGE_SIZE = settings.app.max_page_size

# Uploads
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Storage sub-directories (relative to storage.root)
RESUME_STORAGE_DIR = "resumes"
PROFILE_PHOTO_STORAGE_DIR = "profile_photos"

# Resume chunking / ingestion — values come from settings/config.yaml
RESUME_CHUNK_SIZE_CHARS = settings.resume.chunk_size_chars
RESUME_CHUNK_OVERLAP_CHARS = settings.resume.chunk_overlap_chars
RESUME_INGESTION_TIMEOUT_SECONDS = settings.resume.ingestion_timeout_seconds

# Auth
AUTH_HEADER_PREFIX = "Bearer"  # noqa: S105 - not a secret, just the scheme name
