from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.storage.schema import SchemaManager
from app.storage.unit_of_work import UserUnitOfWork


class JourneyMoodStorageTests(unittest.TestCase):
    @staticmethod
    def _add_playthrough(database: Path) -> None:
        with sqlite3.connect(database) as connection:
            connection.execute(
                """INSERT INTO user_items VALUES(
                'u1','game','Game',2026,NULL,'2026-01-01','2026-01-01',0)"""
            )
            connection.execute(
                """INSERT INTO playthroughs VALUES(
                'p1','user','u1',1,'playing','2026-01-01',NULL,0,
                NULL,NULL,1,NULL)"""
            )
            connection.commit()

    def test_old_schema_one_database_gets_idempotent_user_extension(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "user.db"
            SchemaManager().create_user(database)
            with sqlite3.connect(database) as connection:
                connection.execute("DROP TABLE journey_stage_moods")
                connection.commit()
            manager = SchemaManager()
            manager.ensure_aw023_user_extensions(database)
            manager.ensure_aw023_user_extensions(database)
            with sqlite3.connect(database) as connection:
                self.assertIsNotNone(connection.execute(
                    """SELECT 1 FROM sqlite_master WHERE type='table'
                    AND name='journey_stage_moods'"""
                ).fetchone())

    def test_mood_can_be_written_changed_and_cleared(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "user.db"
            SchemaManager().create_user(database)
            with sqlite3.connect(database) as connection:
                connection.execute(
                    """INSERT INTO user_items VALUES(
                    'u1','game','Game',2026,NULL,'2026-01-01','2026-01-01',0)"""
                )
                connection.execute(
                    """INSERT INTO playthroughs VALUES(
                    'p1','user','u1',1,'playing','2026-01-01',NULL,0,
                    NULL,NULL,1,NULL)"""
                )
                connection.commit()
            with UserUnitOfWork(database) as uow:
                uow.journey_moods.set("p1", "stage-03", "happy", "2026-01-01")
            with UserUnitOfWork(database) as uow:
                self.assertEqual(
                    uow.journey_moods.list_for_playthrough("p1"),
                    {"stage-03": "happy"},
                )
                uow.journey_moods.set("p1", "stage-03", "neutral", "2026-01-02")
            with UserUnitOfWork(database) as uow:
                self.assertEqual(
                    uow.journey_moods.list_for_playthrough("p1")["stage-03"],
                    "neutral",
                )
                uow.journey_moods.clear("p1", "stage-03")
            with UserUnitOfWork(database) as uow:
                self.assertEqual(uow.journey_moods.list_for_playthrough("p1"), {})

    def test_catalog_schema_never_contains_personal_mood(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "catalog.db"
            SchemaManager().create_catalog(database)
            with sqlite3.connect(database) as connection:
                self.assertIsNone(connection.execute(
                    """SELECT 1 FROM sqlite_master WHERE type='table'
                    AND name='journey_stage_moods'"""
                ).fetchone())

    def test_explicit_stage_state_persists_and_updates(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "user.db"
            SchemaManager().create_user(database)
            self._add_playthrough(database)
            with UserUnitOfWork(database) as uow:
                uow.journey_stage_states.set(
                    "p1", "stage-03", "current", "2026-01-01"
                )
            with UserUnitOfWork(database) as uow:
                self.assertEqual(
                    uow.journey_stage_states.list_for_playthrough("p1"),
                    {"stage-03": "current"},
                )
                uow.journey_stage_states.set(
                    "p1", "stage-03", "completed", "2026-01-02"
                )
            with UserUnitOfWork(database) as uow:
                self.assertEqual(
                    uow.journey_stage_states.list_for_playthrough("p1")["stage-03"],
                    "completed",
                )

    def test_invalid_stage_state_is_rejected_before_sql(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "user.db"
            SchemaManager().create_user(database)
            self._add_playthrough(database)
            with self.assertRaises(ValueError), UserUnitOfWork(database) as uow:
                uow.journey_stage_states.set(
                    "p1", "stage-03", "broken", "2026-01-01"
                )

    def test_catalog_schema_never_contains_personal_stage_state(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "catalog.db"
            SchemaManager().create_catalog(database)
            with sqlite3.connect(database) as connection:
                self.assertIsNone(connection.execute(
                    """SELECT 1 FROM sqlite_master WHERE type='table'
                    AND name='journey_stage_states'"""
                ).fetchone())

    def test_explicit_stage_rating_and_flags_are_independent(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "user.db"
            SchemaManager().create_user(database)
            self._add_playthrough(database)
            with UserUnitOfWork(database) as uow:
                uow.journey_stage_ratings.set("p1", "stage-03", 40, "2026-01-01")
                uow.journey_stage_flags.set(
                    "p1", "stage-03", favorite=True, difficult=False,
                    updated_at="2026-01-01",
                )
            with UserUnitOfWork(database) as uow:
                self.assertEqual(
                    uow.journey_stage_ratings.list_for_playthrough("p1"),
                    {"stage-03": 40},
                )
                self.assertEqual(
                    uow.journey_stage_flags.list_for_playthrough("p1"),
                    {"stage-03": (True, False)},
                )

    def test_aw023_extensions_add_rating_and_flags_idempotently(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            database = Path(root) / "user.db"
            SchemaManager().create_user(database)
            with sqlite3.connect(database) as connection:
                connection.execute("DROP TABLE journey_stage_ratings")
                connection.execute("DROP TABLE journey_stage_flags")
                connection.commit()
            manager = SchemaManager()
            manager.ensure_aw023_user_extensions(database)
            manager.ensure_aw023_user_extensions(database)
            with sqlite3.connect(database) as connection:
                names = {row[0] for row in connection.execute(
                    """SELECT name FROM sqlite_master WHERE type='table'
                    AND name IN ('journey_stage_ratings','journey_stage_flags')"""
                )}
            self.assertEqual(
                names, {"journey_stage_ratings", "journey_stage_flags"}
            )


if __name__ == "__main__":
    unittest.main()
