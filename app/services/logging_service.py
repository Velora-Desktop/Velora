from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.core.paths import LOGS_DIR, ensure_runtime_directories


def configure_logging() -> None:
    ensure_runtime_directories()
    root = logging.getLogger()
    if any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        return
    handler = RotatingFileHandler(
        LOGS_DIR / "velora.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
