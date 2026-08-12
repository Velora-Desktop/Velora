from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from PySide6.QtWidgets import QApplication

from app.application.doom_vertical_slice import DoomVerticalSlice, GameJourneySlice
from app.application.game_services import LibraryService
from app.application.journey_presentation import JourneyPresentationBuilder
from app.core.paths import AppPaths
from app.storage.models import CatalogItem
from app.storage.schema import utc_now
from app.storage.startup import DOOM_ETERNAL_ID, prepare_aw02_storage
from app.storage.unit_of_work import CatalogUnitOfWork
from app.ui.game_detail.journey_widgets import JourneyView
from velora_contracts.enums import CatalogLifecycleState, MediaType, SourceType
from velora_contracts.ids import OperationId
from velora_contracts.value_objects import CatalogItemRef


class UniversalJourneyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = prepare_aw02_storage(
            AppPaths.source_run(root=Path(self.temp.name))
        )

    def tearDown(self):
        self.temp.cleanup()

    def add_game(self, game_id: str, title: str, count: int) -> GameJourneySlice:
        game_id = str(uuid5(NAMESPACE_URL, f"velora-test:{game_id}"))
        now = utc_now()
        payload = {
            "payload_version": 1,
            "template_id": "story_campaign",
            "name": f"{title} Journey",
            "stages": [
                {"stable_id": f"stage-{index:02d}",
                 "title": f"Этап {index:02d}", "visible": True}
                for index in range(1, count + 1)
            ],
        }
        with CatalogUnitOfWork(self.storage.catalog_db) as uow:
            uow.catalog.add(CatalogItem(
                game_id, MediaType.GAME, title, title.casefold(), 2026,
                title, title, CatalogLifecycleState.ACTIVE, 1, now, now,
            ))
            uow.catalog.upsert_payload(
                game_id, "journey_template", 1,
                json.dumps(payload, ensure_ascii=False),
            )
        ref = CatalogItemRef(SourceType.OFFICIAL, game_id)
        LibraryService(self.storage.catalog_db, self.storage.user_db).add(
            ref, OperationId.new()
        )
        return GameJourneySlice(self.storage.catalog_db, self.storage.user_db, ref)

    def test_doom_reference_stays_thirteen_stage_legacy_compatible(self):
        model = JourneyPresentationBuilder().build(
            DoomVerticalSlice(self.storage.catalog_db, self.storage.user_db).load_detail()
        )
        self.assertEqual(model.game_id, DOOM_ETERNAL_ID)
        self.assertEqual(len(model.stages), 13)
        self.assertEqual(model.template.template_id, "doom_eternal_reference")

    def test_five_stage_game_supports_state_event_rating_mood_and_persistence(self):
        slice_ = self.add_game("universal-five", "Five Stage Game", 5)
        run = slice_.create_playthrough()
        first_id, second_id = "stage-01", "stage-02"
        slice_.set_stage_state(first_id, "completed", playthrough_id=run)
        slice_.set_stage_rating(first_id, 8, playthrough_id=run)
        slice_.set_stage_mood(first_id, "happy", playthrough_id=run)
        slice_.add_timeline_event(
            first_id, "note", title="Память", body="Только этой игры",
            playthrough_id=run,
        )
        reopened = GameJourneySlice(
            self.storage.catalog_db, self.storage.user_db, slice_.ref
        )
        model = JourneyPresentationBuilder().build(
            reopened.load_detail(), playthrough_id=run
        )
        self.assertEqual(len(model.stages), 5)
        self.assertEqual(model.stages[0].state, "completed")
        self.assertEqual(model.stages[1].state, "current")
        self.assertEqual(model.stages[0].rating, 8)
        self.assertEqual(model.stages[0].mood_id, "happy")
        self.assertEqual(model.stages[0].entries[0].body, "Только этой игры")
        self.assertEqual(model.stages[1].stage_id, second_id)

    def test_twenty_plus_stages_use_same_view_and_horizontal_route(self):
        slice_ = self.add_game("universal-long", "Long Game", 21)
        run = slice_.create_playthrough()
        model = JourneyPresentationBuilder().build(
            slice_.load_detail(), playthrough_id=run
        )
        view = JourneyView()
        view.resize(1200, 720)
        view.set_presentation(model)
        view.show()
        self.app.processEvents()
        self.assertEqual(len(model.stages), 21)
        self.assertEqual(len(view._stage_buttons), 21)
        self.assertGreater(
            view.timeline_scroll.horizontalScrollBar().maximum(), 0
        )

    def test_personal_data_never_crosses_between_games(self):
        first = self.add_game("isolated-a", "Isolated A", 5)
        second = self.add_game("isolated-b", "Isolated B", 5)
        run = first.create_playthrough()
        first.add_timeline_event(
            "stage-01", "note", body="secret-a",
            playthrough_id=run,
        )
        second_model = JourneyPresentationBuilder().build(second.load_detail())
        self.assertFalse(second_model.playthroughs)
        self.assertFalse(any(
            entry.body == "secret-a"
            for stage in second_model.stages for entry in stage.entries
        ))


if __name__ == "__main__":
    unittest.main()
