from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QSettings

from app.core.paths import APP_DATA_DIR, BACKUPS_DIR, LOGS_DIR, USER_IMAGES_DIR, ensure_runtime_directories


LOGGER = logging.getLogger(__name__)
APP_VERSION = "AW0.08"
MAX_AUTOMATIC_BACKUPS = 10


class BackupValidationError(ValueError):
    pass


class DataBackupService:
    def __init__(
        self,
        user_db: Path,
        catalog_db: Path,
        settings: QSettings | None = None,
        *,
        backups_dir: Path = BACKUPS_DIR,
        user_images_dir: Path = USER_IMAGES_DIR,
    ) -> None:
        ensure_runtime_directories()
        self.user_db = Path(user_db)
        self.catalog_db = Path(catalog_db)
        self.settings = settings or QSettings("Velora", "Velora")
        self.backups_dir = Path(backups_dir)
        self.user_images_dir = Path(user_images_dir)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.user_images_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def integrity_check(database: Path) -> tuple[bool, str]:
        try:
            with closing(sqlite3.connect(database)) as connection:
                rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
            ok = rows == ["ok"]
            message = "База исправна." if ok else "Обнаружены ошибки: " + "; ".join(rows)
            LOGGER.info("Integrity check %s: %s", database, message)
            return ok, message
        except Exception as exc:
            LOGGER.exception("Integrity check failed for %s", database)
            return False, f"Проверка не выполнена: {exc}"

    def export_backup(self, destination: Path | None = None, *, automatic: bool = False) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destination = Path(destination or self.backups_dir / f"Velora_Backup_{timestamp}.zip")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="velora_backup_") as temporary:
            root = Path(temporary)
            files: list[Path] = []
            if self.user_db.exists():
                snapshot = root / "user.db"
                with closing(sqlite3.connect(self.user_db)) as source, closing(sqlite3.connect(snapshot)) as target:
                    source.backup(target)
                ok, message = self.integrity_check(snapshot)
                if not ok:
                    raise BackupValidationError(f"Резервная копия не создана: {message}")
                files.append(snapshot)
            settings_path = root / "settings.json"
            settings_path.write_text(
                json.dumps({key: self._json_value(self.settings.value(key)) for key in self.settings.allKeys()}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            files.append(settings_path)
            if self.user_images_dir.exists():
                for source in self.user_images_dir.rglob("*"):
                    if source.is_file():
                        target = root / "images" / source.relative_to(self.user_images_dir)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
                        files.append(target)
            schema = self._schema_version(root / "user.db")
            metadata = {
                "velora_version": APP_VERSION,
                "schema_version": schema,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "automatic": automatic,
                "files": [str(path.relative_to(root)).replace("\\", "/") for path in files],
                "checksums": {str(path.relative_to(root)).replace("\\", "/"): self._sha256(path) for path in files},
            }
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary_zip = destination.with_suffix(destination.suffix + ".tmp")
            with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(metadata_path, "metadata.json")
                for path in files:
                    archive.write(path, str(path.relative_to(root)).replace("\\", "/"))
            temporary_zip.replace(destination)
        if automatic:
            self._rotate_automatic_backups()
        LOGGER.info("Backup exported: %s", destination)
        return destination

    def import_backup(self, archive_path: Path) -> None:
        archive_path = Path(archive_path)
        with tempfile.TemporaryDirectory(prefix="velora_restore_") as temporary:
            root = Path(temporary)
            metadata = self._validate_archive(archive_path, root)
            incoming_db = root / "user.db"
            current_schema = self._schema_version(self.user_db)
            incoming_schema = str(metadata.get("schema_version", "0"))
            if self._version_number(incoming_schema) > self._version_number(current_schema):
                raise BackupValidationError("Схема резервной копии новее установленной версии Velora.")
            self.export_backup(automatic=True)
            if incoming_db.exists():
                replacement = self.user_db.with_suffix(".db.restore")
                shutil.copy2(incoming_db, replacement)
                ok, message = self.integrity_check(replacement)
                if not ok:
                    replacement.unlink(missing_ok=True)
                    raise BackupValidationError(message)
                replacement.replace(self.user_db)
            settings_path = root / "settings.json"
            if settings_path.exists():
                values = json.loads(settings_path.read_text(encoding="utf-8"))
                self.settings.clear()
                for key, value in values.items():
                    self.settings.setValue(key, value)
                self.settings.sync()
            images = root / "images"
            if self.user_images_dir.exists():
                shutil.rmtree(self.user_images_dir)
            if images.exists():
                shutil.copytree(images, self.user_images_dir)
            else:
                self.user_images_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Backup imported: %s", archive_path)

    def storage_sizes(self) -> dict[str, int]:
        values = {
            "catalog": self.catalog_db.stat().st_size if self.catalog_db.exists() else 0,
            "covers": self._directory_size(self.catalog_db.parent.parent / "assets" / "covers"),
            "user_db": self.user_db.stat().st_size if self.user_db.exists() else 0,
            "user_images": self._directory_size(self.user_images_dir),
            "backups": self._directory_size(self.backups_dir),
        }
        values["total"] = sum(values.values())
        return values

    def versions(self) -> dict[str, str]:
        return {
            "application": APP_VERSION,
            "user_schema": self._schema_version(self.user_db),
            "catalog_schema": self._schema_version(self.catalog_db),
        }

    def _validate_archive(self, archive_path: Path, root: Path) -> dict:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    target = (root / member.filename).resolve()
                    if root.resolve() not in target.parents and target != root.resolve():
                        raise BackupValidationError("Архив содержит небезопасный путь.")
                archive.extractall(root)
        except (OSError, zipfile.BadZipFile) as exc:
            raise BackupValidationError(f"Некорректный архив: {exc}") from exc
        metadata_path = root / "metadata.json"
        if not metadata_path.exists():
            raise BackupValidationError("В архиве отсутствует metadata.json.")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not {"velora_version", "schema_version", "created_at", "files", "checksums"}.issubset(metadata):
            raise BackupValidationError("metadata.json не содержит обязательные поля Velora.")
        required = {"user.db", "settings.json"}
        if not required.issubset(set(metadata.get("files", []))):
            raise BackupValidationError("Резервная копия не содержит user.db и settings.json.")
        for relative in metadata.get("files", []):
            path = root / relative
            if not path.is_file():
                raise BackupValidationError(f"Отсутствует файл: {relative}")
            expected = metadata.get("checksums", {}).get(relative)
            if not expected or self._sha256(path) != expected:
                raise BackupValidationError(f"Не совпала контрольная сумма: {relative}")
        return metadata

    def _rotate_automatic_backups(self) -> None:
        backups = sorted(self.backups_dir.glob("Velora_Backup_*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        for old in backups[MAX_AUTOMATIC_BACKUPS:]:
            old.unlink(missing_ok=True)

    @staticmethod
    def _directory_size(path: Path) -> int:
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _json_value(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, tuple)):
            return [DataBackupService._json_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): DataBackupService._json_value(item) for key, item in value.items()}
        return str(value)

    @staticmethod
    def _schema_version(path: Path) -> str:
        if not path.exists():
            return "0"
        try:
            with closing(sqlite3.connect(path)) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "schema_migrations" in tables:
                    row = connection.execute("SELECT MAX(CAST(version AS INTEGER)) FROM schema_migrations").fetchone()
                    return str(row[0] or 0)
                if "metadata" in tables:
                    row = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
                    return str(row[0]) if row else "0"
                return "0"
        except sqlite3.Error:
            return "0"

    @staticmethod
    def _version_number(value: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
