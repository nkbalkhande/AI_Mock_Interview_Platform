"""Logging configuration.

Call ``configure_logging()`` once at application startup. Keeps a simple,
readable format for development; JSON/structured logging can be swapped in
later without touching call sites.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.core.config import settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = (settings.logging.level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    if settings.logging.file_path:
        log_path = Path(settings.logging.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Show per-request access logs in development so API calls are visible;
    # keep them quiet in production to avoid noise.
    logging.getLogger("uvicorn.access").setLevel(
        logging.INFO if settings.app.debug else logging.WARNING
    )
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.postgres.echo else logging.WARNING
    )

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
