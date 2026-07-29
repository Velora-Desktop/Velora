"""Verified snapshot primitives usable before reset and migration engines."""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from velora_contracts.canonical_json import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from velora_contracts.enums import SnapshotType
from velora_contracts.errors import BackupError, IntegrityError
from velora_contracts.ids import OperationId, SnapshotId
from velora_contracts.validators import validate_relative_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SnapshotInfo:
    snapshot_id: str
    snapshot_type: SnapshotType
    path: Path
    manifest_path: Path
    database_checksum: str
    created_at: str
    source_schema_version: int
    core_generation: int
    parent_operation_id: str


class SnapshotVerifier:
    def verify(self, snapshot_path: Path) -> SnapshotInfo:
        import json

        root = Path(snapshot_path)
        manifest_path = root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("Snapshot manifest is missing or unreadable") from exc
        required = {
            "snapshot_id",
            "snapshot_type",
            "created_at",
            "database_file",
            "database_checksum_sha256",
            "source_schema_version",
            "core_generation",
            "parent_operation_id",
            "media_entries",
            "aggregate_sha256",
        }
        if not isinstance(manifest, dict) or set(manifest) != required:
            raise IntegrityError("Snapshot manifest contains missing or unknown fields")
        try:
            SnapshotId(str(manifest["snapshot_id"]))
            SnapshotType(manifest["snapshot_type"])
            OperationId(str(manifest["parent_operation_id"]))
        except Exception as exc:
            raise IntegrityError("Snapshot manifest contains invalid identifiers") from exc
        if (
            manifest["database_file"] != "database.db"
            or not isinstance(manifest["source_schema_version"], int)
            or manifest["source_schema_version"] < 0
            or not isinstance(manifest["core_generation"], int)
            or manifest["core_generation"] < 0
        ):
            raise IntegrityError("Snapshot manifest contains invalid source metadata")
        database = root / manifest["database_file"]
        if not database.is_file() or sha256_file(database) != manifest["database_checksum_sha256"]:
            raise IntegrityError("Snapshot database checksum mismatch")
        try:
            connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
            try:
                integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
                foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise IntegrityError("Snapshot database cannot be verified") from exc
        if integrity != ["ok"] or foreign_keys:
            raise IntegrityError("Snapshot database failed SQLite verification")
        entries = manifest["media_entries"]
        if not isinstance(entries, list):
            raise IntegrityError("Snapshot media_entries must be an array")
        for entry in entries:
            relative = entry.get("relative_path")
            try:
                safe_relative = validate_relative_path(relative)
            except Exception as exc:
                raise IntegrityError("Snapshot media path is unsafe") from exc
            path = root / safe_relative
            if (
                not isinstance(entry, dict)
                or set(entry) != {"relative_path", "sha256", "byte_length"}
                or not path.is_file()
                or path.stat().st_size != entry["byte_length"]
                or sha256_file(path) != entry["sha256"]
            ):
                raise IntegrityError("Snapshot media verification failed")
        aggregate_source = {
            key: value for key, value in manifest.items() if key != "aggregate_sha256"
        }
        if sha256_bytes(canonical_json_bytes(aggregate_source)) != manifest["aggregate_sha256"]:
            raise IntegrityError("Snapshot aggregate checksum mismatch")
        return SnapshotInfo(
            snapshot_id=manifest["snapshot_id"],
            snapshot_type=SnapshotType(manifest["snapshot_type"]),
            path=root,
            manifest_path=manifest_path,
            database_checksum=manifest["database_checksum_sha256"],
            created_at=manifest["created_at"],
            source_schema_version=manifest["source_schema_version"],
            core_generation=manifest["core_generation"],
            parent_operation_id=manifest["parent_operation_id"],
        )


class SnapshotCreator:
    def __init__(self, verifier: SnapshotVerifier | None = None) -> None:
        self.verifier = verifier or SnapshotVerifier()

    def create(
        self,
        database_path: Path,
        destination_root: Path,
        *,
        snapshot_type: SnapshotType,
        source_schema_version: int,
        core_generation: int,
        parent_operation_id: OperationId | str,
        media_path: Path | None = None,
    ) -> SnapshotInfo:
        source_db = Path(database_path)
        if not source_db.is_file():
            raise BackupError(f"Snapshot source database does not exist: {source_db}")
        snapshot_id = str(uuid4())
        operation_id = OperationId(str(parent_operation_id))
        if source_schema_version < 0 or core_generation < 0:
            raise BackupError("Snapshot schema/core generation cannot be negative")
        destination_root = Path(destination_root)
        destination_root.mkdir(parents=True, exist_ok=True)
        final = destination_root / snapshot_id
        temporary = destination_root / f".{snapshot_id}.tmp"
        created_at = _utc_now()
        try:
            temporary.mkdir()
            copied_db = temporary / "database.db"
            source = sqlite3.connect(f"file:{source_db.resolve().as_posix()}?mode=ro", uri=True)
            target = sqlite3.connect(copied_db)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            media_entries: list[dict[str, object]] = []
            if media_path and Path(media_path).exists():
                media_root = Path(media_path)
                for item in sorted(path for path in media_root.rglob("*") if path.is_file()):
                    relative = Path("media") / item.relative_to(media_root)
                    target_path = temporary / relative
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_path)
                    media_entries.append(
                        {
                            "relative_path": relative.as_posix(),
                            "sha256": sha256_file(target_path),
                            "byte_length": target_path.stat().st_size,
                        }
                    )
            manifest = {
                "snapshot_id": snapshot_id,
                "snapshot_type": SnapshotType(snapshot_type).value,
                "created_at": created_at,
                "database_file": "database.db",
                "database_checksum_sha256": sha256_file(copied_db),
                "source_schema_version": source_schema_version,
                "core_generation": core_generation,
                "parent_operation_id": str(operation_id),
                "media_entries": media_entries,
            }
            manifest["aggregate_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
            manifest_path = temporary / "manifest.json"
            with manifest_path.open("wb") as stream:
                stream.write(canonical_json_bytes(manifest))
                stream.flush()
                os.fsync(stream.fileno())
            self.verifier.verify(temporary)
            os.replace(temporary, final)
            return self.verifier.verify(final)
        except Exception as exc:
            shutil.rmtree(temporary, ignore_errors=True)
            if isinstance(exc, (BackupError, IntegrityError)):
                raise
            raise BackupError("Snapshot creation failed; source was left untouched") from exc
