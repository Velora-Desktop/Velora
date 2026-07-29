"""Idempotent AW0.2 one-time reset boundary."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import gc
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from velora_contracts.canonical_json import sha256_bytes, sha256_file
from velora_contracts.enums import SnapshotType
from velora_contracts.errors import FatalStorageError, IntegrityError
from velora_contracts.ids import OperationId

from app.core.paths import AppPaths

from .recovery import AtomicJsonJournal
from .schema import SchemaManager
from .snapshots import SnapshotCreator, SnapshotVerifier


class ResetHardStop(FatalStorageError):
    """Unsafe or ambiguous filesystem state; source data remains untouched."""


class SimulatedResetInterruption(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResetResult:
    operation_id: str
    state: str
    generation_path: Path
    resumed: bool


def _tree_hashes(root: Path | None) -> dict[str, str]:
    if root is None or not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*")) if path.is_file()
    }

def _sqlite_logical_hash(path: Path) -> str:
    connection = sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        payload = "\n".join(connection.iterdump()).encode("utf-8")
        return sha256_bytes(payload)
    finally:
        connection.close()


class AW02ResetManager:
    STATES = (
        "legacy_detected", "snapshot_verified", "legacy_archived",
        "schema_created", "completed",
    )

    def __init__(
        self, paths: AppPaths, *, schema: SchemaManager | None = None,
        snapshots: SnapshotCreator | None = None,
    ) -> None:
        self.paths = paths
        self.schema = schema or SchemaManager()
        self.snapshots = snapshots or SnapshotCreator()
        self.verifier = SnapshotVerifier()
        self.journal = AtomicJsonJournal(paths.reset_recovery_journal)

    def start_or_resume(
        self, *, operation_id: str | None = None,
        interrupt_after: str | None = None,
    ) -> ResetResult:
        self.paths.ensure_runtime_directories()
        state = self.journal.read()
        resumed = state is not None
        if state is None:
            op = str(OperationId(operation_id)) if operation_id else str(OperationId.new())
            source_db = (
                self.paths.legacy_user_db
                if self.paths.legacy_user_db.is_file()
                else self.paths.user_db
            )
            if not source_db.is_file():
                raise ResetHardStop("Legacy user database was not found")
            state = {
                "operation_id": op,
                "state": "legacy_detected",
                "source_db": str(source_db),
                "source_media": str(self.paths.user_media),
                "source_db_sha256": sha256_file(source_db),
                "source_db_logical_sha256": _sqlite_logical_hash(source_db),
                "source_media_hashes": _tree_hashes(self.paths.user_media),
                "archive_path": str(self.paths.legacy / op),
                "new_generation_path": str(self.paths.profile_generations / op),
                "snapshot_path": None,
                "last_error": None,
            }
            self.journal.write(state)
            self._interrupt(state, interrupt_after)
        while state["state"] != "completed":
            current = state["state"]
            if current == "legacy_detected":
                self._snapshot(state)
                state["state"] = "snapshot_verified"
            elif current == "snapshot_verified":
                self._archive(state)
                state["state"] = "legacy_archived"
            elif current == "legacy_archived":
                self._create_generation(state)
                state["state"] = "schema_created"
            elif current == "schema_created":
                self._activate(state)
                state["state"] = "completed"
            else:
                raise ResetHardStop(f"Unknown reset state: {current}")
            self.journal.write(state)
            self._interrupt(state, interrupt_after)
        return ResetResult(
            state["operation_id"], state["state"],
            Path(state["new_generation_path"]), resumed,
        )

    def _interrupt(self, state: dict[str, object], expected: str | None) -> None:
        if expected == state["state"]:
            raise SimulatedResetInterruption(str(expected))

    def _snapshot(self, state: dict[str, object]) -> None:
        existing = state.get("snapshot_path")
        if existing:
            info = self.verifier.verify(Path(str(existing)))
            if info.parent_operation_id != state["operation_id"]:
                raise ResetHardStop("Existing reset snapshot belongs to another operation")
            return
        info = self.snapshots.create(
            Path(str(state["source_db"])), self.paths.snapshots,
            snapshot_type=SnapshotType.LEGACY_RESET,
            source_schema_version=0, core_generation=0,
            parent_operation_id=str(state["operation_id"]),
            media_path=Path(str(state["source_media"])),
        )
        if _sqlite_logical_hash(info.path / "database.db") != state["source_db_logical_sha256"]:
            raise ResetHardStop("Verified snapshot does not match recorded legacy database")
        state["snapshot_path"] = str(info.path)
        self.journal.write(state)

    def _archive(self, state: dict[str, object]) -> None:
        source_db = Path(str(state["source_db"]))
        source_media = Path(str(state["source_media"]))
        archive = Path(str(state["archive_path"]))
        archived_db = archive / "user.db"
        archived_media = archive / "media"
        if source_db.exists() and archived_db.exists():
            raise ResetHardStop("Legacy source and archive both exist")
        if not source_db.exists() and not archived_db.exists():
            raise ResetHardStop("Neither legacy source nor expected archive exists")
        if archived_db.exists():
            if sha256_file(archived_db) != state["source_db_sha256"]:
                self._diagnostic(state, "archive checksum mismatch")
                raise ResetHardStop("Existing archive does not match legacy database")
            if _tree_hashes(archived_media) != state["source_media_hashes"]:
                self._diagnostic(state, "archive media checksum mismatch")
                raise ResetHardStop("Existing archive media does not match legacy media")
            return
        archive.mkdir(parents=True, exist_ok=False)
        # CPython's sqlite cursor finalizers can lag behind Connection.close on
        # Windows. Collect before the required atomic rename so no read handle
        # from snapshot verification remains attached to the legacy file.
        gc.collect()
        os.replace(source_db, archived_db)
        if source_media.exists():
            os.replace(source_media, archived_media)
        if sha256_file(archived_db) != state["source_db_sha256"]:
            raise ResetHardStop("Archived legacy database failed verification")
        if _tree_hashes(archived_media) != state["source_media_hashes"]:
            raise ResetHardStop("Archived legacy media failed verification")

    def _create_generation(self, state: dict[str, object]) -> None:
        generation = Path(str(state["new_generation_path"]))
        database = generation / "user.db"
        if generation.exists():
            try:
                self.schema.validate(
                    database, expected_operation_id=str(state["operation_id"])
                )
                return
            except Exception:
                if database.exists() and self._operation_id(database) not in (
                    None, str(state["operation_id"])
                ):
                    raise ResetHardStop("Generation belongs to another reset operation")
                quarantine = self.paths.profile_quarantine / (
                    generation.name + "-" + uuid4().hex
                )
                quarantine.parent.mkdir(parents=True, exist_ok=True)
                os.replace(generation, quarantine)
        generation.mkdir(parents=True)
        self.schema.create_user(database, reset_operation_id=str(state["operation_id"]))

    def _activate(self, state: dict[str, object]) -> None:
        generation = Path(str(state["new_generation_path"]))
        self.schema.validate(
            generation / "user.db", expected_operation_id=str(state["operation_id"])
        )
        pointer = {
            "operation_id": state["operation_id"],
            "generation_path": str(generation),
            "core_generation": 1,
        }
        AtomicJsonJournal(self.paths.active_profile_pointer).write(pointer)
        if AtomicJsonJournal(self.paths.active_profile_pointer).read() != pointer:
            raise ResetHardStop("Profile generation pointer activation was not durable")

    def _operation_id(self, database: Path) -> str | None:
        try:
            connection = self.schema.policy.connect(database, read_only=True)
            try:
                row = connection.execute(
                    "SELECT reset_operation_id FROM schema_meta WHERE singleton_id=1"
                ).fetchone()
                return row[0] if row else None
            finally:
                connection.close()
        except Exception:
            return None

    def _diagnostic(self, state: dict[str, object], message: str) -> None:
        state["last_error"] = message
        self.journal.write(state)
