"""Durable external JSON journals used by later recovery engines."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from velora_contracts.canonical_json import canonical_json_bytes
from velora_contracts.errors import IntegrityError, RecoverableStorageError


class AtomicJsonJournal:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            with temporary.open("wb") as stream:
                stream.write(canonical_json_bytes(payload))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self._fsync_parent()
        except OSError as exc:
            raise RecoverableStorageError(
                f"Could not persist recovery journal: {self.path}"
            ) from exc

    def read(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError(f"Recovery journal is unreadable: {self.path}") from exc
        if not isinstance(value, dict):
            raise IntegrityError("Recovery journal root must be an object")
        return value

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
            self._fsync_parent()
        except OSError as exc:
            raise RecoverableStorageError(
                f"Could not clear recovery journal: {self.path}"
            ) from exc

    def _fsync_parent(self) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
