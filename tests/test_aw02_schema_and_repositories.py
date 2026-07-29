from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.storage.models import (
    CatalogItem, Impression, JourneyEvent, LibraryState, Playthrough, Rating, UserItem,
)
from app.storage.schema import SchemaManager, utc_now
from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork
from velora_contracts.canonical_json import canonical_json_text
from velora_contracts.enums import (
    CatalogLifecycleState, LibraryMembershipState, MediaType, RatingType, SourceType,
)
from velora_contracts.ids import (
    CatalogId, EventId, OperationId, PlaythroughId, RatingId, UserItemId,
)
from uuid import uuid4


class SchemaAndRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.catalog_db = self.root / "catalog.db"
        self.user_db = self.root / "user.db"
        manager = SchemaManager()
        manager.create_catalog(self.catalog_db)
        manager.create_user(self.user_db, reset_operation_id=str(OperationId.new()))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_schema_metadata_constraints_fts_and_integrity(self) -> None:
        for path, fts in ((self.catalog_db, "catalog_fts"), (self.user_db, "user_fts")):
            connection = sqlite3.connect(path)
            try:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_meta").fetchone()[0], 1)
                self.assertIsNotNone(connection.execute(
                    "SELECT name FROM sqlite_master WHERE name=?", (fts,)
                ).fetchone())
            finally:
                connection.close()
        connection = sqlite3.connect(self.user_db)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """INSERT INTO playthroughs VALUES(
                    'a','official','x',1,'playing',NULL,NULL,-1,NULL,NULL,1,NULL)"""
                )
        finally:
            connection.close()

    def test_end_to_end_transaction_and_restart(self) -> None:
        now = utc_now()
        catalog_id = str(CatalogId.new())
        user_id = str(UserItemId.new())
        playthrough_id = str(PlaythroughId.new())
        operation_id = str(OperationId.new())
        with CatalogUnitOfWork(self.catalog_db) as uow:
            uow.catalog.add(CatalogItem(
                catalog_id, MediaType.GAME, "Test Game", "test game", 2026,
                "short", "description", CatalogLifecycleState.ACTIVE, 1, now, now,
            ))
        with UserUnitOfWork(self.user_db) as uow:
            uow.user_items.add(UserItem(
                user_id, MediaType.GAME, "Local Test", 2026, None, now, now, False
            ))
            uow.library.upsert(LibraryState(
                SourceType.OFFICIAL, catalog_id, LibraryMembershipState.ACTIVE,
                False, "playing", None, None, 45, now, None, None, now,
            ))
            uow.playthroughs.add(Playthrough(
                playthrough_id, SourceType.OFFICIAL, catalog_id, 1, "playing",
                now, None, 45, None, None, True, None,
            ))
            uow.journey.append(JourneyEvent(
                str(EventId.new()), operation_id, SourceType.OFFICIAL, catalog_id,
                playthrough_id, "playthrough_started", 1,
                canonical_json_text({"status": "playing"}), now,
            ))
            rating_id = str(RatingId.new())
            uow.ratings.add(Rating(
                rating_id, SourceType.OFFICIAL, catalog_id, playthrough_id,
                RatingType.CHECKPOINT, "start", 75, "First impression",
                True, None, now, now,
            ))
            impression_id = str(uuid4())
            uow.impressions.add(Impression(
                impression_id, playthrough_id, None, "Journal note",
                None, None, 45, now,
            ))
        with CatalogUnitOfWork(self.catalog_db) as uow:
            self.assertEqual(uow.catalog.get(catalog_id).canonical_title, "Test Game")
        with UserUnitOfWork(self.user_db) as uow:
            self.assertEqual(uow.library.get(SourceType.OFFICIAL, catalog_id).projected_total_playtime_minutes, 45)
            self.assertEqual(uow.playthroughs.get(playthrough_id).status, "playing")
            self.assertEqual(uow.journey.get_by_operation(operation_id).event_type, "playthrough_started")
            self.assertEqual(uow.user_items.get(user_id).title, "Local Test")
            self.assertEqual(uow.impressions.get(impression_id).text, "Journal note")

    def test_rollback_has_no_partial_state(self) -> None:
        now = utc_now()
        item_id = str(CatalogId.new())
        playthrough_id = str(PlaythroughId.new())
        with self.assertRaisesRegex(RuntimeError, "injected"):
            with UserUnitOfWork(self.user_db) as uow:
                uow.library.upsert(LibraryState(
                    SourceType.OFFICIAL, item_id, LibraryMembershipState.ACTIVE,
                    False, "playing", None, None, 10, now, None, None, now,
                ))
                uow.playthroughs.add(Playthrough(
                    playthrough_id, SourceType.OFFICIAL, item_id, 1, "playing",
                    now, None, 10, None, None, True, None,
                ))
                raise RuntimeError("injected")
        with UserUnitOfWork(self.user_db) as uow:
            self.assertIsNone(uow.library.get(SourceType.OFFICIAL, item_id))
            self.assertIsNone(uow.playthroughs.get(playthrough_id))

    def test_repositories_do_not_commit_hidden_transactions(self) -> None:
        now = utc_now()
        item_id = str(CatalogId.new())
        connection = sqlite3.connect(self.catalog_db, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        from app.storage.repositories import CatalogRepository
        connection.execute("BEGIN IMMEDIATE")
        CatalogRepository(connection).add(CatalogItem(
            item_id, MediaType.GAME, "Rollback", "rollback", None, None, None,
            CatalogLifecycleState.ACTIVE, 1, now, now,
        ))
        connection.rollback()
        self.assertEqual(connection.execute(
            "SELECT COUNT(*) FROM catalog_items WHERE catalog_id=?", (item_id,)
        ).fetchone()[0], 0)
        connection.close()


if __name__ == "__main__":
    unittest.main()
