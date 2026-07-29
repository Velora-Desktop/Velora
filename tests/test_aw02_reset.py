from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core.paths import AppPaths
from app.storage.recovery import AtomicJsonJournal
from app.storage.reset import AW02ResetManager, ResetHardStop, SimulatedResetInterruption
from app.storage.schema import SchemaManager
from velora_contracts.canonical_json import sha256_file
from velora_contracts.ids import OperationId


def legacy_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE legacy_data(value TEXT)")
        connection.execute("INSERT INTO legacy_data VALUES('preserve me')")
        connection.commit()
    finally:
        connection.close()


class ResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.paths = AppPaths.source_run(root=Path(self.temp.name))
        self.paths.ensure_runtime_directories()
        legacy_database(self.paths.user_db)
        (self.paths.user_media / "cover.txt").write_text("media", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_first_reset_and_completed_second_launch(self) -> None:
        manager = AW02ResetManager(self.paths)
        result = manager.start_or_resume()
        self.assertEqual(result.state, "completed")
        self.assertFalse(self.paths.user_db.exists())
        self.assertTrue((result.generation_path / "user.db").exists())
        self.assertTrue((self.paths.legacy / result.operation_id / "user.db").exists())
        second = manager.start_or_resume()
        self.assertTrue(second.resumed)
        self.assertEqual(second.operation_id, result.operation_id)
        SchemaManager().validate(
            second.generation_path / "user.db",
            expected_operation_id=second.operation_id,
        )

    def test_resume_after_snapshot_verified(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="snapshot_verified")
        result = manager.start_or_resume()
        self.assertEqual(result.state, "completed")

    def test_resume_after_legacy_archived(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="legacy_archived")
        state = AtomicJsonJournal(self.paths.reset_recovery_journal).read()
        self.assertFalse(Path(state["source_db"]).exists())
        self.assertTrue((Path(state["archive_path"]) / "user.db").exists())
        self.assertEqual(manager.start_or_resume().state, "completed")

    def test_existing_valid_archive_is_idempotent(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="legacy_archived")
        state = AtomicJsonJournal(self.paths.reset_recovery_journal).read()
        state["state"] = "snapshot_verified"
        AtomicJsonJournal(self.paths.reset_recovery_journal).write(state)
        self.assertEqual(manager.start_or_resume().state, "completed")

    def test_existing_valid_generation_is_reused(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="schema_created")
        state = AtomicJsonJournal(self.paths.reset_recovery_journal).read()
        database = Path(state["new_generation_path"]) / "user.db"
        before = sha256_file(database)
        state["state"] = "legacy_archived"
        AtomicJsonJournal(self.paths.reset_recovery_journal).write(state)
        manager.start_or_resume()
        self.assertEqual(sha256_file(database), before)

    def test_partial_generation_is_quarantined(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="legacy_archived")
        state = AtomicJsonJournal(self.paths.reset_recovery_journal).read()
        generation = Path(state["new_generation_path"])
        generation.mkdir(parents=True)
        (generation / "partial").write_text("x")
        manager.start_or_resume()
        self.assertTrue(any(self.paths.profile_quarantine.iterdir()))
        self.assertTrue((generation / "user.db").exists())

    def test_mismatched_generation_hard_stops(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="legacy_archived")
        state = AtomicJsonJournal(self.paths.reset_recovery_journal).read()
        generation = Path(state["new_generation_path"])
        generation.mkdir(parents=True)
        SchemaManager().create_user(
            generation / "user.db", reset_operation_id=str(OperationId.new())
        )
        with self.assertRaises(ResetHardStop):
            manager.start_or_resume()
        self.assertTrue((generation / "user.db").exists())

    def test_unexpected_archive_path_hard_stops_without_source_deletion(self) -> None:
        manager = AW02ResetManager(self.paths)
        with self.assertRaises(SimulatedResetInterruption):
            manager.start_or_resume(interrupt_after="snapshot_verified")
        state = AtomicJsonJournal(self.paths.reset_recovery_journal).read()
        archive = Path(state["archive_path"])
        archive.mkdir(parents=True)
        legacy_database(archive / "user.db")
        with self.assertRaises(ResetHardStop):
            manager.start_or_resume()
        self.assertTrue(self.paths.user_db.exists())
        self.assertTrue((archive / "user.db").exists())


if __name__ == "__main__":
    unittest.main()
