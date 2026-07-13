from __future__ import annotations

import os
import json
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = {
    "catalog_id", "media_type", "title", "category", "subgroup",
    "age_rating", "general_score", "is_active", "updated_at",
}


@dataclass(frozen=True, slots=True)
class CatalogUpdateResult:
    catalog_version: str
    item_count: int
    backup_path: Path | None


@dataclass(frozen=True, slots=True)
class CatalogChange:
    version: str
    added: dict[str, int]
    updated: int = 0
    removed: int = 0
    published_at: str = ""


class CatalogUpdateService:
    """Validate and atomically install a catalog-only micro-patch."""

    def install(self, package: Path, destination: Path) -> CatalogUpdateResult:
        package = package.resolve()
        destination = destination.resolve()
        if not package.is_file():
            raise FileNotFoundError(package)

        version, item_count = self._validate(package)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".update")
        backup = destination.with_suffix(destination.suffix + ".bak")
        temporary.unlink(missing_ok=True)
        shutil.copy2(package, temporary)

        backup_path = None
        if destination.exists():
            shutil.copy2(destination, backup)
            backup_path = backup
        os.replace(temporary, destination)
        return CatalogUpdateResult(version, item_count, backup_path)

    @staticmethod
    def history(catalog: Path) -> list[CatalogChange]:
        if not catalog.exists():
            return []
        connection = sqlite3.connect(f"file:{catalog.as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute("SELECT value FROM metadata WHERE key='update_history'").fetchone()
            if not row:
                return []
            values = json.loads(row[0])
            return [
                CatalogChange(
                    version=str(value.get("version", "без версии")),
                    added={str(key): int(count) for key, count in value.get("added", {}).items()},
                    updated=int(value.get("updated", 0)),
                    removed=int(value.get("removed", 0)),
                    published_at=str(value.get("published_at", "")),
                )
                for value in values
            ]
        except (sqlite3.Error, json.JSONDecodeError, TypeError, ValueError):
            return []
        finally:
            connection.close()

    @staticmethod
    def _validate(package: Path) -> tuple[str, int]:
        connection = sqlite3.connect(f"file:{package.as_posix()}?mode=ro", uri=True)
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Повреждённый файл каталога")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"catalog_items", "metadata"} <= tables:
                raise ValueError("Файл не является каталогом Velora")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(catalog_items)")}
            missing = REQUIRED_COLUMNS - columns
            if missing:
                raise ValueError(f"В каталоге отсутствуют колонки: {', '.join(sorted(missing))}")
            row = connection.execute("SELECT value FROM metadata WHERE key='catalog_version'").fetchone()
            version = row[0] if row else "legacy"
            item_count = connection.execute("SELECT COUNT(*) FROM catalog_items WHERE is_active=1").fetchone()[0]
            return version, int(item_count)
        finally:
            connection.close()
