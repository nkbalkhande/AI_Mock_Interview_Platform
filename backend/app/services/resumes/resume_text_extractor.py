"""Resume text extraction (AD-15).

Docling handles PDF/DOC/DOCX; plain-text uploads are read directly. Docling
pulls in heavy ML dependencies (torch, layout models), so the import is
lazy and the converter is built once per process on first use, not at
module load time — importing this module must stay cheap.
"""

from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_PLAIN_TEXT_TYPES = frozenset({"text/plain"})

_converter = None  # type: ignore[var-annotated]  # lazily-built docling.DocumentConverter


def _get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter

        _converter = DocumentConverter()
    return _converter


def extract_text(file_path: Path, content_type: str) -> str:
    """Return plain-ish text for a resume file, or "" if extraction fails.

    Never raises: a bad/corrupt resume file must not break registration or
    the background ingestion task. Callers should treat an empty result as
    "extraction unavailable" and skip embedding.
    """
    if not file_path.exists():
        logger.warning("Resume file missing on disk: %s", file_path)
        return ""

    try:
        if content_type in _PLAIN_TEXT_TYPES:
            return file_path.read_text(encoding="utf-8", errors="ignore").strip()

        converter = _get_converter()
        result = converter.convert(str(file_path))
        return result.document.export_to_markdown().strip()
    except Exception:  # noqa: BLE001 - extraction must degrade, never crash
        logger.exception("Resume text extraction failed for %s", file_path)
        return ""
