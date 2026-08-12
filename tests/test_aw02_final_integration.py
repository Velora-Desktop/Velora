from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.application.doom_vertical_slice import DoomVerticalSlice
from app.application.game_row_queries import GamesRowQueryService
from app.core.paths import AppPaths
from app.storage.startup import DOOM_ETERNAL_ID, prepare_aw02_storage
from velora_contracts.enums import CheckpointType, SourceType
from velora_contracts.value_objects import CatalogItemRef


class FinalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.paths = AppPaths.source_run(root=Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_root_profile_is_snapshotted_archived_and_idempotent(self):
        legacy = self.paths.legacy_user_db
        legacy.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(legacy)
        try:
            db.execute("CREATE TABLE legacy_value(value TEXT)")
            db.execute("INSERT INTO legacy_value VALUES('keep me')")
            db.commit()
        finally:
            db.close()
        first = prepare_aw02_storage(self.paths)
        self.assertTrue(first.reset_performed)
        self.assertFalse(legacy.exists())
        self.assertTrue(any(self.paths.snapshots.iterdir()))
        archived = list(self.paths.legacy.glob("*/user.db"))
        self.assertEqual(len(archived), 1)
        db = sqlite3.connect(archived[0])
        try:
            self.assertEqual(db.execute("SELECT value FROM legacy_value").fetchone()[0], "keep me")
        finally:
            db.close()
        second = prepare_aw02_storage(self.paths)
        self.assertEqual(second.user_db, first.user_db)
        self.assertFalse(second.reset_performed)

    def test_full_doom_scenario_survives_restart(self):
        storage = prepare_aw02_storage(self.paths)
        slice_ = DoomVerticalSlice(storage.catalog_db, storage.user_db)
        slice_.set_status("ПРОХОЖУ")
        slice_.set_total_playtime_hours(2.5)
        slice_.add_checkpoint(CheckpointType.MIDDLE)
        slice_.add_impression("Промежуточное впечатление")
        slice_.save_final_rating({"gameplay": 9, "music": 8})
        slice_.set_status("ПРОШЁЛ")
        reopened = prepare_aw02_storage(self.paths)
        query = GamesRowQueryService(reopened.catalog_db, reopened.user_db)
        state = query.get_game_row(
            CatalogItemRef(SourceType.OFFICIAL, DOOM_ETERNAL_ID)
        )
        self.assertEqual(state.row.playthrough_status, "completed")
        self.assertEqual(state.row.total_playtime_minutes, 150)
        self.assertEqual(state.row.current_personal_rating_tenths, 85)
        self.assertEqual(state.row.latest_impression_preview, "Промежуточное впечатление")
        detail = slice_.load_detail()
        self.assertEqual(len(detail.playthroughs), 1)
        self.assertEqual(detail.playthroughs[0].checkpoint, "middle")
        self.assertEqual(len(detail.impressions), 1)
        self.assertGreaterEqual(len(detail.ratings), 1)
        self.assertTrue(any(event.title == "Прохождение завершено" for event in detail.journey))

        slice_.set_status("ПРОХОЖУ")
        repeated = slice_.load_detail()
        self.assertEqual(len(repeated.playthroughs), 2)
        self.assertEqual(repeated.playthroughs[-1].sequence_no, 2)
        self.assertEqual(repeated.playthroughs[-1].status, "playing")
        slice_.set_status("НЕ НАЧИНАЛ")
        reset = slice_.load_detail()
        self.assertEqual(reset.playthroughs[-1].status, "planned")

    def test_studio_bridge_changes_catalog_but_not_user_database(self):
        studio_root = Path(r"C:\Velora studio")
        sys.path.insert(0, str(studio_root))
        try:
            from studio.services.aw02_catalog_bridge import AW02CatalogBridge
            storage = prepare_aw02_storage(self.paths)
            before = storage.user_db.read_bytes()
            item = SimpleNamespace(
                catalog_id="g-shooter-fps-002",
                title="Doom Eternal",
                release_year=2020,
                description="Проверенное описание Studio 0.1",
            )
            journey_configuration = SimpleNamespace(
                official_payload=lambda: {
                    "payload_version": 1,
                    "template_id": "story_campaign",
                    "name": "Кампания из Studio",
                    "stages": [
                        {"number": 1, "title": "Пролог", "visible": True},
                        {"number": 2, "title": "Финал", "visible": True},
                    ],
                }
            )
            self.assertTrue(
                AW02CatalogBridge(self.paths).save_if_supported(
                    item, journey_configuration
                )
            )
            self.assertEqual(storage.user_db.read_bytes(), before)
            db = sqlite3.connect(storage.catalog_db)
            try:
                self.assertEqual(
                    db.execute(
                        "SELECT description FROM catalog_items WHERE catalog_id=?",
                        (DOOM_ETERNAL_ID,),
                    ).fetchone()[0],
                    item.description,
                )
                payload = db.execute(
                    """SELECT payload_json FROM catalog_payloads
                    WHERE catalog_id=? AND payload_type='journey_template'""",
                    (DOOM_ETERNAL_ID,),
                ).fetchone()
                self.assertIsNotNone(payload)
                self.assertEqual(
                    json.loads(payload[0])["stages"][0]["title"], "Пролог"
                )
            finally:
                db.close()
        finally:
            sys.path.remove(str(studio_root))


if __name__ == "__main__":
    unittest.main()
