"""Application-wide constant values.

Domain enumerations (interview status, roles, etc.) live in
``app.domain.enums``. This module holds framework/infra-level constants.
"""

from __future__ import annotations

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Uploads
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Storage sub-directories (relative to STORAGE_ROOT)
RESUME_STORAGE_DIR = "resumes"
PROFILE_PHOTO_STORAGE_DIR = "profile_photos"

# Resume chunking (for embedding into Qdrant).
RESUME_CHUNK_SIZE_CHARS = 1000
RESUME_CHUNK_OVERLAP_CHARS = 150

# Background ingestion timeout — a hung parse/embed call must never wedge the
# process; we bail and log rather than block forever. Generous because
# Docling's *first* run on a fresh machine downloads its layout/OCR models
# (one-time, then cached under ~/.cache/huggingface); later runs are seconds.
RESUME_INGESTION_TIMEOUT_SECONDS = 600

# Auth
AUTH_HEADER_PREFIX = "Bearer"  # noqa: S105 - not a secret, just the scheme name
