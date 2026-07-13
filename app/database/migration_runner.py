from __future__ import annotations

import sqlite3
from pathlib import Path


class MigrationRunner:
    """Apply ordered, idempotent SQL files and record completed versions."""

    def __init__(self, migrations_dir: Path) -> None:
        self.migrations_dir = migrations_dir

    def migrate(self, database: Path) -> list[str]:
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database)
        applied_now: list[str] = []
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(self.migrations_dir.glob("[0-9][0-9][0-9]_*.sql")):
                version = migration.stem.split("_", 1)[0]
                if version in applied:
                    continue
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version) VALUES(?)", (version,))
                connection.commit()
                applied_now.append(version)
            return applied_now
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
