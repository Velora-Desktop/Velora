from __future__ import annotations

import sqlite3
import logging
from contextlib import closing
from datetime import datetime
from pathlib import Path

from app.core.paths import BACKUPS_DIR, ensure_runtime_directories


LOGGER = logging.getLogger(__name__)


class MigrationRunner:
    """Apply ordered, idempotent SQL files and record completed versions."""

    def __init__(self, migrations_dir: Path, backup_dir: Path = BACKUPS_DIR) -> None:
        self.migrations_dir = migrations_dir
        self.backup_dir = backup_dir

    def migrate(self, database: Path) -> list[str]:
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database)
        applied_now: list[str] = []
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            pending = [migration for migration in sorted(self.migrations_dir.glob("[0-9][0-9][0-9]_*.sql")) if migration.stem.split("_", 1)[0] not in applied]
            if pending and database.exists() and database.stat().st_size:
                self._backup_before_migration(connection, database)
            for migration in pending:
                version = migration.stem.split("_", 1)[0]
                script = migration.read_text(encoding="utf-8")
                safe_version = version.replace("'", "''")
                connection.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + script
                    + f"\nINSERT INTO schema_migrations(version) VALUES('{safe_version}');\nCOMMIT;"
                )
                recorded = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version=?", (version,)
                ).fetchone()
                if not recorded:
                    raise RuntimeError(f"Migration {version} was not recorded")
                applied_now.append(version)
                LOGGER.info("Applied migration %s to %s", version, database)
            return applied_now
        except Exception:
            connection.rollback()
            LOGGER.exception("Migration failed for %s", database)
            raise
        finally:
            connection.close()

    def _backup_before_migration(self, connection: sqlite3.Connection, database: Path) -> Path:
        ensure_runtime_directories()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        backup = self.backup_dir / f"before_migration_{database.stem}_{timestamp}.db"
        with closing(sqlite3.connect(backup)) as target:
            connection.backup(target)
        backups = sorted(
            self.backup_dir.glob(f"before_migration_{database.stem}_*.db"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old in backups[10:]:
            old.unlink(missing_ok=True)
        return backup
