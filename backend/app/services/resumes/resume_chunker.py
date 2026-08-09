"""Splits extracted resume text into overlapping chunks for embedding.

A resume is short (a page or two), so this is a simple sliding character
window rather than a token-aware splitter — good enough for MVP retrieval
and avoids pulling in another tokenizer dependency.
"""

from __future__ import annotations

from app.core.constants import RESUME_CHUNK_OVERLAP_CHARS, RESUME_CHUNK_SIZE_CHARS


def chunk_text(
    text: str,
    *,
    chunk_size: int = RESUME_CHUNK_SIZE_CHARS,
    overlap: int = RESUME_CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """Split ``text`` into overlapping chunks, dropping empty/whitespace-only ones."""
    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == length:
            break
        start += step
    return chunks
