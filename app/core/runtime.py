"""Process-local runtime wiring set by the source entry point."""
from __future__ import annotations

from app.storage.startup import StartupStorage

_storage: StartupStorage | None = None


def set_startup_storage(storage: StartupStorage) -> None:
    global _storage
    _storage = storage


def startup_storage() -> StartupStorage | None:
    return _storage
