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

# Resume chunking (for embedding into Qdrant). A resume is 1-2 pages
# (~3-6k chars); text-embedding-3-small supports up to ~8191 tokens
# (~30k+ chars), so the size is set well above any real resume's length —
# in practice every resume becomes exactly one chunk/embedding. The
# sliding-window split only kicks in as a safety net for the rare
# oversized/garbled extraction, so we don't silently drop content or blow
# past the model's token limit.
RESUME_CHUNK_SIZE_CHARS = 20000
RESUME_CHUNK_OVERLAP_CHARS = 500

# Background ingestion timeout — a hung parse/embed call must never wedge the
# process; we bail and log rather than block forever. Generous because
# Docling's *first* run on a fresh machine downloads its layout/OCR models
# (one-time, then cached under ~/.cache/huggingface); later runs are seconds.
RESUME_INGESTION_TIMEOUT_SECONDS = 600

# Auth
AUTH_HEADER_PREFIX = "Bearer"  # noqa: S105 - not a secret, just the scheme name
