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

# Auth
AUTH_HEADER_PREFIX = "Bearer"  # noqa: S105 - not a secret, just the scheme name
