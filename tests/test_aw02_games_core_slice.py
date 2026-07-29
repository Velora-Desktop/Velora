from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.application import (
    GameProgressService, GameRowReadModel, ImpressionService,
    InProcessEventDispatcher, JourneyService, LibraryService,
    PlaythroughService, RatingService,
)
from app.storage.models import CatalogItem
from app.storage.repositories import JourneyRepository
from app.storage.schema import SchemaManager
from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork
from velora_contracts.enums import (
    CatalogLifecycleState, CheckpointType, MediaType, SourceType,
)
from velora_contracts.errors import ConflictError
from velora_contracts.ids import CatalogId, OperationId
from velora_contracts.value_objects import CatalogItemRef


class GamesCoreSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.catalog_db, self.user_db = root / "catalog.db", root / "user.db"
        manager = SchemaManager()
        manager.create_catalog(self.catalog_db)
        manager.create_user(self.user_db, reset_operation_id=str(OperationId.new()))
        self.ref = CatalogItemRef(SourceType.OFFICIAL, str(CatalogId.new()))
        with CatalogUnitOfWork(self.catalog_db) as uow:
            uow.catalog.add(CatalogItem(
                self.ref.item_id, MediaType.GAME, "Smoke Game", "smoke game",
                2026, "short", "description", CatalogLifecycleState.ACTIVE,
                1, self.at(0), self.at(0),
            ))
        self.events = []
        self.dispatcher = InProcessEventDispatcher()
        self.dispatcher.subscribe(self.events.append)
        self.library = LibraryService(
            self.catalog_db, self.user_db, dispatcher=self.dispatcher
        )
        self.playthroughs = PlaythroughService(
            self.user_db, dispatcher=self.dispatcher
        )
        self.progress = GameProgressService(self.user_db, dispatcher=self.dispatcher)
        self.impressions = ImpressionService(
            self.user_db, dispatcher=self.dispatcher
        )
        self.ratings = RatingService(self.user_db, dispatcher=self.dispatcher)
        self.journey = JourneyService(self.user_db, dispatcher=self.dispatcher)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def at(second: int) -> str:
        return f"2026-01-01T00:00:{second:02d}Z"

    @staticmethod
    def op() -> str:
        return str(OperationId.new())

    def add(self):
        return self.library.add(self.ref, self.op(), occurred_at=self.at(1))

    def create(self):
        self.add()
        return self.playthroughs.create(
            self.ref, self.op(), initial_status="planned", started_at=self.at(2)
        )

    def full(self):
        self.add()
        run = self.playthroughs.create(
            self.ref, self.op(), initial_status="planned", started_at=self.at(2)
        )
        run = self.playthroughs.set_status(
            run.playthrough_id, "playing", self.op(), occurred_at=self.at(3)
        )
        run = self.playthroughs.add_playtime(
            run.playthrough_id, 90, self.op(), occurred_at=self.at(4)
        )
        self.progress.create_checkpoint(
            run.playthrough_id, CheckpointType.START, self.op(),
            occurred_at=self.at(5),
        )
        self.impressions.create(
            run.playthrough_id, "A strong first impression", self.op(),
            checkpoint_type=CheckpointType.START,
            playtime_minutes_at_entry=90, occurred_at=self.at(6),
        )
        self.ratings.save_checkpoint(
            run.playthrough_id, CheckpointType.START, self.op(),
            value_tenths=75, occurred_at=self.at(7),
        )
        run = self.playthroughs.set_status(
            run.playthrough_id, "completed", self.op(), occurred_at=self.at(8)
        )
        self.ratings.save_final(
            self.ref, 88, {"gameplay": 90, "story": 80}, self.op(),
            playthrough_id=run.playthrough_id, occurred_at=self.at(9),
        )
        return run

    def test_01_add_game_to_library(self) -> None:
        state = self.add()
        self.assertEqual(state.item_id, self.ref.item_id)
        self.assertEqual(self.events[-1].event_name, "LibraryItemAdded.v1")

    def test_02_repeated_add_does_not_duplicate(self) -> None:
        operation = self.op()
        first = self.library.add(self.ref, operation, occurred_at=self.at(1))
        second = self.library.add(self.ref, operation, occurred_at=self.at(1))
        self.assertEqual(first, second)
        with UserUnitOfWork(self.user_db) as uow:
            self.assertEqual(len(uow.library.list_all()), 1)
            self.assertEqual(len(uow.journey.list_for_item(
                self.ref.source_type, self.ref.item_id
            )), 1)

    def test_03_create_playthrough(self) -> None:
        run = self.create()
        self.assertEqual(run.status, "planned")
        self.assertEqual(run.sequence_no, 1)

    def test_04_illegal_status_transition(self) -> None:
        run = self.create()
        with self.assertRaises(ConflictError):
            self.playthroughs.set_status(
                run.playthrough_id, "completed", self.op(), occurred_at=self.at(3)
            )

    def test_05_add_playtime(self) -> None:
        run = self.create()
        run = self.playthroughs.set_status(
            run.playthrough_id, "playing", self.op(), occurred_at=self.at(3)
        )
        result = self.playthroughs.add_playtime(
            run.playthrough_id, 45, self.op(), occurred_at=self.at(4)
        )
        self.assertEqual(result.playtime_minutes, 45)

    def test_06_create_checkpoint(self) -> None:
        run = self.create()
        result = self.progress.create_checkpoint(
            run.playthrough_id, "start", self.op(), occurred_at=self.at(3)
        )
        self.assertEqual(result, "start")

    def test_07_add_impression(self) -> None:
        run = self.create()
        value = self.impressions.create(
            run.playthrough_id, "Text", self.op(), occurred_at=self.at(3)
        )
        self.assertEqual(value.text, "Text")
        self.assertIsNone(value.checkpoint_type)

    def test_08_rating_history_and_supersede(self) -> None:
        run = self.create()
        first = self.ratings.save_final(
            self.ref, 70, {}, self.op(), playthrough_id=run.playthrough_id,
            occurred_at=self.at(3),
        )
        second = self.ratings.save_final(
            self.ref, 85, {}, self.op(), playthrough_id=run.playthrough_id,
            occurred_at=self.at(4),
        )
        with UserUnitOfWork(self.user_db) as uow:
            history = uow.ratings.history(self.ref.source_type, self.ref.item_id)
        self.assertEqual([rating.value_tenths for rating in history], [70, 85])
        self.assertFalse(history[0].is_current)
        self.assertTrue(history[1].is_current)
        self.assertEqual(history[0].superseded_at, self.at(4))
        self.assertNotEqual(first.rating_id, second.rating_id)

    def test_09_complete_playthrough(self) -> None:
        run = self.create()
        run = self.playthroughs.set_status(
            run.playthrough_id, "playing", self.op(), occurred_at=self.at(3)
        )
        run = self.playthroughs.set_status(
            run.playthrough_id, "completed", self.op(), occurred_at=self.at(4)
        )
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.ended_at, self.at(4))

    def test_10_projection_and_journey_atomic_rollback(self) -> None:
        self.add()
        before_events = len(self.events)
        with patch.object(JourneyRepository, "append", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.playthroughs.create(
                    self.ref, self.op(), initial_status="planned",
                    started_at=self.at(2),
                )
        with UserUnitOfWork(self.user_db) as uow:
            self.assertIsNone(uow.playthroughs.get_current(
                self.ref.source_type, self.ref.item_id
            ))
            self.assertIsNone(uow.library.get(
                self.ref.source_type, self.ref.item_id
            ).projected_status)
        self.assertEqual(len(self.events), before_events)

    def test_11_post_commit_event_not_emitted_on_rollback(self) -> None:
        self.add()
        delivered = len(self.events)
        with patch.object(JourneyRepository, "append", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.playthroughs.start(
                    self.ref, self.op(), started_at=self.at(2)
                )
        self.assertEqual(len(self.events), delivered)

    def test_12_correct_journey_order(self) -> None:
        self.full()
        values = self.journey.list_for_game(self.ref)
        self.assertEqual(
            [event.event_type for event in values],
            [
                "library_added", "playthrough_started", "status_changed",
                "playtime_added", "milestone_recorded", "impression_added",
                "rating_changed", "playthrough_completed", "rating_changed",
            ],
        )

    def test_13_reopen_persistence(self) -> None:
        self.full()
        reopened = JourneyService(self.user_db)
        row = reopened.get_game_row(self.catalog_db, self.ref)
        self.assertEqual(row.playthrough_status, "completed")
        self.assertEqual(row.total_playtime_minutes, 90)
        self.assertEqual(row.current_personal_rating_tenths, 88)

    def test_14_game_row_read_model(self) -> None:
        self.full()
        row = self.journey.get_game_row(self.catalog_db, self.ref)
        self.assertIsInstance(row, GameRowReadModel)
        self.assertEqual(row.title, "Smoke Game")
        self.assertEqual(row.current_checkpoint, "start")
        self.assertEqual(row.latest_impression_preview, "A strong first impression")

    def test_15_application_slice_has_no_ui_or_pyside_imports(self) -> None:
        root = Path(__file__).parents[1] / "app" / "application"
        forbidden = []
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                forbidden.extend(
                    name for name in names
                    if name.startswith(("PySide6", "app.ui"))
                )
        self.assertEqual(forbidden, [])


if __name__ == "__main__":
    unittest.main()
