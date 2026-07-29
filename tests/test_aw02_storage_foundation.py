from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app.core.paths import AppPaths
from app.storage.recovery import AtomicJsonJournal
from app.storage.snapshots import SnapshotCreator, SnapshotVerifier
from app.storage.sqlite_policy import SQLitePolicy
from velora_contracts.enums import SnapshotType
from velora_contracts.errors import BackupError


class StorageFoundationTests(unittest.TestCase):
    def test_app_paths_are_rooted_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = AppPaths.source_run(root=Path(temporary) / "profile")
            paths.ensure_runtime_directories()
            self.assertEqual(paths.catalog_db, paths.root / "data" / "catalog.db")
            self.assertEqual(
                paths.patch_recovery_journal,
                paths.root / "runtime" / "patch_recovery_state.json",
            )
            self.assertTrue(paths.user_media.is_dir())
            self.assertTrue(paths.snapshots.is_dir())

    def test_sqlite_policy_enables_foreign_keys_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "test.db"
            policy = SQLitePolicy(busy_timeout_ms=3210)
            connection = policy.connect(database)
            try:
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                self.assertEqual(connection.execute("PRAGMA busy_timeout").fetchone()[0], 3210)
                connection.execute("CREATE TABLE values_table(value TEXT)")
            finally:
                connection.close()
            with self.assertRaises(RuntimeError):
                with policy.session(database) as session:
                    session.execute("INSERT INTO values_table VALUES ('not committed')")
                    raise RuntimeError("simulate failure")
            check = policy.connect(database, read_only=True)
            try:
                self.assertEqual(check.execute("SELECT COUNT(*) FROM values_table").fetchone()[0], 0)
            finally:
                check.close()

    def test_atomic_recovery_journal_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = AtomicJsonJournal(Path(temporary) / "runtime" / "state.json")
            payload = {"protocol_version": 1, "state": "verified"}
            journal.write(payload)
            self.assertEqual(journal.read(), payload)
            journal.clear()
            self.assertIsNone(journal.read())

    def test_snapshot_copy_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "user.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
                connection.execute("INSERT INTO sample(value) VALUES ('preserved')")
                connection.commit()
            media = root / "media"
            media.mkdir()
            (media / "note.txt").write_text("media", encoding="utf-8")
            info = SnapshotCreator().create(
                database,
                root / "snapshots",
                snapshot_type=SnapshotType.PRE_MIGRATION,
                source_schema_version=1,
                core_generation=1,
                parent_operation_id="11111111-1111-4111-8111-111111111111",
                media_path=media,
            )
            verified = SnapshotVerifier().verify(info.path)
            self.assertEqual(verified.snapshot_id, info.snapshot_id)
            with closing(sqlite3.connect(info.path / "database.db")) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM sample").fetchone()[0],
                    "preserved",
                )

    def test_snapshot_failure_preserves_original(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "user.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE sample(value TEXT)")
                connection.execute("INSERT INTO sample VALUES ('original')")
                connection.commit()
            with patch.object(
                SnapshotVerifier, "verify", side_effect=RuntimeError("simulated verifier failure")
            ):
                with self.assertRaises(BackupError):
                    SnapshotCreator().create(
                        database,
                        root / "snapshots",
                        snapshot_type=SnapshotType.LEGACY_RESET,
                        source_schema_version=0,
                        core_generation=0,
                        parent_operation_id="22222222-2222-4222-8222-222222222222",
                    )
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM sample").fetchone()[0],
                    "original",
                )
            self.assertFalse(list((root / "snapshots").glob(".*.tmp")))


class ImportBoundaryTests(unittest.TestCase):
    def test_foundation_has_no_qt_or_ui_imports(self) -> None:
        project = Path(__file__).resolve().parents[1]
        roots = [project / "velora_contracts", project / "app" / "storage"]
        forbidden = ("PySide", "app.ui", "studio.ui")
        offenders: list[str] = []
        for root in roots:
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if any(name in text for name in forbidden):
                    offenders.append(str(path.relative_to(project)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
