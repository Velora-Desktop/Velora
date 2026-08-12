from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from app.application.doom_vertical_slice import DoomVerticalSlice
from app.application.journey_presentation import JourneyPresentationBuilder
from app.application.journey_layout import JourneyTimelineLayoutModel
from app.application.playthrough_history import (
    GamePlaythroughHistoryQueryService,
)
from app.core.paths import AppPaths
from app.storage.startup import prepare_aw02_storage
from app.storage.unit_of_work import UserUnitOfWork
from app.ui.game_detail.doom_aw02_panel import DoomAw02Panel
from app.ui.game_detail.journey_widgets import JourneyStageArtwork, JourneyView


class PlaythroughFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        paths = AppPaths.source_run(root=Path(self.temp.name))
        self.storage = prepare_aw02_storage(paths)
        self.slice = DoomVerticalSlice(
            self.storage.catalog_db, self.storage.user_db
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_new_runs_are_inserted_and_keep_independent_journey_data(self):
        first = self.slice.create_playthrough()
        self.slice.set_stage_state(
            "stage-01", "completed", playthrough_id=first
        )
        self.slice.set_stage_mood(
            "stage-01", "happy", playthrough_id=first
        )
        self.slice.add_impression(
            "Первое воспоминание", progress_value=1,
            progress_unit="journey_stage", playthrough_id=first,
        )
        self.slice.save_personal_rating(7.5, playthrough_id=first)

        second = self.slice.create_playthrough()
        third = self.slice.create_playthrough()
        state = self.slice.load_detail()

        self.assertEqual([item.sequence_no for item in state.playthroughs], [1, 2, 3])
        self.assertEqual(len({item.playthrough_id for item in state.playthroughs}), 3)
        self.assertEqual(state.row.current_playthrough_id, third)
        first_model = JourneyPresentationBuilder().build(
            state, playthrough_id=first
        )
        second_model = JourneyPresentationBuilder().build(
            state, playthrough_id=second
        )
        self.assertEqual(first_model.stages[0].state, "completed")
        self.assertEqual(first_model.stages[0].mood_id, "happy")
        self.assertTrue(first_model.impressions)
        self.assertEqual(second_model.stages[0].mood_id, None)
        self.assertFalse(second_model.impressions)

    def test_completing_current_stage_advances_next_stage_atomically(self):
        playthrough_id = self.slice.create_playthrough()
        self.slice.set_stage_state(
            "stage-01", "completed", playthrough_id=playthrough_id
        )
        with UserUnitOfWork(self.storage.user_db) as uow:
            states = uow.journey_stage_states.list_for_playthrough(playthrough_id)
        self.assertEqual(states["stage-01"], "completed")
        self.assertEqual(states["stage-02"], "current")

    def test_completing_non_current_stage_does_not_move_current_stage(self):
        playthrough_id = self.slice.create_playthrough()
        self.slice.set_stage_state(
            "stage-02", "current", playthrough_id=playthrough_id
        )
        self.slice.set_stage_state(
            "stage-01", "completed", playthrough_id=playthrough_id
        )
        with UserUnitOfWork(self.storage.user_db) as uow:
            states = uow.journey_stage_states.list_for_playthrough(playthrough_id)
        self.assertEqual(states["stage-01"], "completed")
        self.assertEqual(states["stage-02"], "current")

    def test_last_stage_completion_does_not_complete_playthrough_silently(self):
        playthrough_id = self.slice.create_playthrough()
        self.slice.set_stage_state(
            "stage-13", "current", playthrough_id=playthrough_id
        )
        self.slice.set_stage_state(
            "stage-13", "completed", playthrough_id=playthrough_id
        )
        with UserUnitOfWork(self.storage.user_db) as uow:
            run = uow.playthroughs.get(playthrough_id)
            states = uow.journey_stage_states.list_for_playthrough(playthrough_id)
        self.assertEqual(states["stage-13"], "completed")
        self.assertNotEqual(run.status, "completed")

    def test_typed_timeline_event_keeps_type_stage_tags_and_media(self):
        playthrough_id = self.slice.create_playthrough()
        event_id = self.slice.add_timeline_event(
            "stage-03", "screenshot", title="Арена", body="Сильный бой",
            tags=("демоны", "арена"), media_path="media/arena.png",
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        event = model.stages[2].entries[0]
        self.assertEqual(event.source_id, event_id)
        self.assertEqual(event.kind, "screenshot")
        self.assertEqual(event.stage_id, "stage-03")
        self.assertEqual(event.tags, ("демоны", "арена"))
        self.assertEqual(event.media_path, "media/arena.png")

    def test_impression_quick_action_persists_as_its_own_timeline_event(self):
        playthrough_id = self.slice.create_playthrough()
        event_id = self.slice.add_timeline_event(
            "stage-03", "impression", title="Личное впечатление",
            body="Бой ощущается очень динамично", rating_after=8.0,
            mood_id="positive", playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        event = next(
            item for item in model.stages[2].entries
            if item.source_id == event_id
        )
        self.assertEqual(event.kind, "impression")
        self.assertEqual(event.title, "Личное впечатление")
        self.assertEqual(event.rating, 8.0)
        self.assertEqual(event.mood_id, "positive")

    def test_event_ratings_form_stage_average_and_revision_updates_it(self):
        playthrough_id = self.slice.create_playthrough()
        first_id = self.slice.add_timeline_event(
            "stage-03", "note", title="Первое", rating_after=6.0,
            playthrough_id=playthrough_id,
        )
        self.slice.add_timeline_event(
            "stage-03", "achievement", title="Второе", rating_after=8.0,
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        stage = model.stages[2]
        self.assertEqual([entry.rating for entry in stage.entries], [6.0, 8.0])
        from app.ui.game_detail.journey_widgets import _latest_rating
        self.assertEqual(_latest_rating(stage), 7.0)

        self.slice.revise_timeline_event(
            first_id, title="Первое", body="", rating_after=10.0,
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertEqual(_latest_rating(model.stages[2]), 9.0)

        self.slice.set_stage_rating(
            "stage-03", 10.0, playthrough_id=playthrough_id
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertEqual(_latest_rating(model.stages[2]), 10.0)

    def test_timeline_event_keeps_individual_mood_and_rating(self):
        playthrough_id = self.slice.create_playthrough()
        event_id = self.slice.add_timeline_event(
            "stage-03", "other", title="Бой", rating_after=8.0,
            mood_id="happy", playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        event = model.stages[2].entries[0]
        self.assertEqual((event.rating, event.mood_id), (8.0, "happy"))

        self.slice.revise_timeline_event(
            event_id, title="Бой", body="", rating_after=9.0,
            mood_id="excited", playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        event = model.stages[2].entries[0]
        self.assertEqual((event.rating, event.mood_id), (9.0, "excited"))

    def test_timeline_orders_events_by_editable_event_datetime(self):
        playthrough_id = self.slice.create_playthrough()
        later_id = self.slice.add_timeline_event(
            "stage-03", "note", title="Позже",
            occurred_at="2026-08-04T15:30:00",
            playthrough_id=playthrough_id,
        )
        self.slice.add_timeline_event(
            "stage-03", "note", title="Раньше",
            occurred_at="2026-08-04T14:40:00",
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        from app.ui.game_detail.journey_widgets import JourneyView
        ordered = JourneyView._prioritized_entries(model.stages[2])
        self.assertEqual([entry.title for entry in ordered], ["Раньше", "Позже"])

        self.slice.revise_timeline_event(
            later_id, title="Теперь первый", body="",
            occurred_at="2026-08-04T13:15:00",
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        ordered = JourneyView._prioritized_entries(model.stages[2])
        self.assertEqual(
            [(entry.title, entry.occurred_at) for entry in ordered],
            [
                ("Теперь первый", "2026-08-04T13:15:00"),
                ("Раньше", "2026-08-04T14:40:00"),
            ],
        )

    def test_empty_timeline_title_uses_type_specific_label(self):
        playthrough_id = self.slice.create_playthrough()
        self.slice.add_timeline_event(
            "stage-03", "difficult_moment", title="",
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertEqual(model.stages[2].entries[0].title, "Сложный момент")

    def test_technical_events_are_not_visible_on_timeline(self):
        playthrough_id = self.slice.create_playthrough()
        self.slice.set_stage_state(
            "stage-01", "current", playthrough_id=playthrough_id
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertFalse(any(
            entry.kind == "stage_state_changed"
            for stage in model.stages for entry in stage.entries
        ))

    def test_timeline_event_revision_and_delete_are_projected(self):
        playthrough_id = self.slice.create_playthrough()
        event_id = self.slice.add_timeline_event(
            "stage-02", "note", title="Черновик", body="Старый текст",
            playthrough_id=playthrough_id,
        )
        self.slice.revise_timeline_event(
            event_id, title="Готово", body="Новый текст", tags=("важное",),
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertEqual(model.stages[1].entries[0].title, "Готово")
        self.assertEqual(model.stages[1].entries[0].body, "Новый текст")
        self.assertEqual(model.stages[1].entries[0].tags, ("важное",))
        self.slice.revise_timeline_event(
            event_id, title="Финальная заметка", body="Последний текст",
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertEqual(model.stages[1].entries[0].title, "Финальная заметка")
        self.assertEqual(model.stages[1].entries[0].body, "Последний текст")
        self.slice.delete_timeline_event(event_id, playthrough_id=playthrough_id)
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertFalse(model.stages[1].entries)

    def test_legacy_impression_revision_and_delete_are_projected(self):
        playthrough_id = self.slice.create_playthrough()
        self.slice.add_impression(
            "Старая заметка", progress_value=3,
            progress_unit="journey_stage", playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        entry = model.impressions[0]
        self.assertTrue(entry.source_id.startswith("impression:"))

        self.slice.revise_timeline_event(
            entry.source_id, title="Заметка", body="Новый текст",
            rating_after=10.0, mood_id="positive",
            playthrough_id=playthrough_id,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        revised = next(
            item for item in model.impressions
            if item.source_id == entry.source_id
        )
        self.assertEqual(revised.body, "Новый текст")
        self.assertEqual(revised.rating, 10.0)
        self.assertEqual(revised.mood_id, "positive")
        self.assertIn(revised, model.stages[2].entries)

        self.slice.delete_timeline_event(
            entry.source_id, playthrough_id=playthrough_id
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        self.assertFalse(any(
            item.source_id == entry.source_id
            for item in model.all_sources
        ))

    def test_dynamic_timeline_segment_threshold(self):
        playthrough_id = self.slice.create_playthrough()
        for index in range(12):
            self.slice.add_timeline_event(
                "stage-01", "note", title=f"Событие {index}",
                playthrough_id=playthrough_id,
            )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        segment = JourneyTimelineLayoutModel.build(model.stages)[0]
        self.assertEqual(segment.event_count, 12)
        self.assertEqual(segment.visible_event_count, 5)
        self.assertEqual(segment.hidden_event_count, 7)
        self.assertGreater(segment.width, JourneyTimelineLayoutModel.EMPTY_WIDTH)

    def test_mission_event_count_matches_timeline_and_ignores_stage_rating(self):
        playthrough_id = self.slice.create_playthrough()
        for index in range(8):
            self.slice.add_timeline_event(
                "stage-01", "note", title=f"Событие {index}",
                playthrough_id=playthrough_id,
            )
        self.slice.set_stage_rating(
            "stage-01", 9.0, playthrough_id=playthrough_id
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        segment = JourneyTimelineLayoutModel.build(model.stages)[0]
        self.assertEqual(segment.event_count, 8)
        self.assertEqual(segment.visible_event_count, 5)
        self.assertEqual(segment.hidden_event_count, 3)

        from app.ui.game_detail.journey_widgets import JourneyTimelineNode
        node = JourneyTimelineNode(model.stages[0], "active", 1)
        self.assertEqual(node.event_count_label.text(), "Событий: 8")

    def test_event_and_group_context_selection_and_refresh(self):
        playthrough_id = self.slice.create_playthrough()
        for index in range(4):
            self.slice.add_timeline_event(
                "stage-03", "note", title=f"Заметка {index}",
                playthrough_id=playthrough_id,
            )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        view = JourneyView()
        view.set_presentation(model)
        entries = model.stages[2].entries
        view._select_event(entries[0])
        self.assertEqual(view._selected_event_id, entries[0].source_id)
        self.assertTrue(view.stage_status.isHidden())
        self.assertTrue(view.quick_impression_caption.isHidden())
        self.assertTrue(all(
            button.isHidden()
            for button in view.quick_impression_buttons.values()
        ))
        view._select_stage("stage-03")
        self.assertFalse(view.stage_status.isHidden())
        self.assertFalse(view.quick_impression_caption.isHidden())
        self.assertTrue(all(
            not button.isHidden()
            for button in view.quick_impression_buttons.values()
        ))
        view._select_event(entries[0])
        view.set_presentation(model)
        self.assertEqual(view._selected_event_id, entries[0].source_id)
        view._select_event_group(entries)
        self.assertEqual(view.detail_title.text(), "СОБЫТИЯ ЭТАПА")

    def test_detail_exposes_quick_impressions_without_generic_tag_editor(self):
        view = JourneyView()
        self.assertEqual(len(view.quick_impression_buttons), 6)
        self.assertFalse(hasattr(view, "tag_preview"))
        self.assertGreaterEqual(view.detail.minimumHeight(), 205)

    def test_quick_impression_emits_typed_stage_bound_draft_once(self):
        playthrough_id = self.slice.create_playthrough()
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        view = JourneyView()
        view.set_presentation(model)
        drafts = []
        view.entry_requested.connect(drafts.append)
        button = view.quick_impression_buttons["Сложная миссия"]
        button.click()
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].stage_id, "stage-01")
        self.assertEqual(drafts[0].event_type, "impression")
        self.assertEqual(drafts[0].title, "Сложная миссия")
        button.click()
        self.assertEqual(len(drafts), 1)

    def test_creator_history_exposes_all_visible_events(self):
        first = self.slice.create_playthrough()
        second = self.slice.create_playthrough()
        self.slice.add_timeline_event(
            "stage-01", "note", title="Первое", playthrough_id=first
        )
        self.slice.add_timeline_event(
            "stage-02", "screenshot", title="Второе", playthrough_id=second
        )
        history = GamePlaythroughHistoryQueryService(
            self.storage.user_db
        ).get(self.slice.ref)
        self.assertEqual(len(history.playthroughs), 2)
        self.assertEqual(
            {event.event_type for event in history.visible_events},
            {"note", "screenshot"},
        )

    def test_stage_art_is_local_and_projected_for_selected_playthrough(self):
        playthrough_id = self.slice.create_playthrough()
        source = Path(self.temp.name) / "stage.png"
        source.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000d4944415408d763f8cfc0f01f00050001ff89993d1d0000000049454e44ae426082"
            )
        )
        target = self.slice.set_stage_media(
            "stage-03", str(source), playthrough_id=playthrough_id,
        )
        self.assertTrue(Path(target).is_file())
        self.assertNotEqual(Path(target), source)
        self.assertEqual(Path(target).read_bytes(), source.read_bytes())
        artwork = JourneyStageArtwork()
        self.assertEqual(
            artwork.width() * JourneyStageArtwork.PREVIEW_HEIGHT,
            artwork.height() * JourneyStageArtwork.PREVIEW_WIDTH,
        )
        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id,
        )
        self.assertEqual(model.stages[2].media_path, str(Path(target).resolve()))
        self.assertIsNone(model.stages[1].media_path)

    def test_history_aggregates_all_runs_not_only_selected_one(self):
        ratings = (7.5, 8.5, 9.0)
        hours = (10, 12, 5)
        ids = []
        for rating, duration in zip(ratings, hours):
            playthrough_id = self.slice.create_playthrough()
            ids.append(playthrough_id)
            self.slice.add_playtime(
                duration, 0, playthrough_id=playthrough_id
            )
            self.slice.save_personal_rating(
                rating, playthrough_id=playthrough_id
            )

        history = GamePlaythroughHistoryQueryService(
            self.storage.user_db
        ).get(self.slice.ref)
        self.assertEqual(history.playthrough_count, 3)
        self.assertEqual(history.total_time_all_playthroughs_minutes, 27 * 60)
        self.assertEqual(
            [item.value_tenths for item in history.ratings], [75, 85, 90]
        )
        self.assertEqual(
            [item.playthrough.playthrough_id for item in history.playthroughs], ids
        )
        self.assertTrue(all(item.last_activity_at for item in history.playthroughs))

    def test_selector_uses_stable_ids_and_supports_more_than_twenty_runs(self):
        for _ in range(21):
            self.slice.create_playthrough()
        state = self.slice.load_detail()
        model = JourneyPresentationBuilder().build(
            state, playthrough_id=state.playthroughs[-1].playthrough_id
        )
        view = JourneyView()
        view.set_presentation(model)
        self.assertEqual(view.run_selector.count(), 21)
        self.assertEqual(
            view.run_selector.currentData(), state.playthroughs[-1].playthrough_id
        )
        self.assertIn("№21", view.run_selector.currentText())
        self.assertEqual(view.run_selector.height(), view.run_actions.height())
        self.assertEqual(view.run_selector_group.height(), 36)
        self.assertEqual(view.run_selector_group.layout().spacing(), 0)
        self.assertGreaterEqual(
            view.run_selector.width(),
            view.run_selector.fontMetrics().horizontalAdvance(
                view.run_selector.currentText()
            ) + 36,
        )

    def test_left_card_subtitles_without_journey_time(self):
        first = self.slice.create_playthrough()
        self.slice.add_playtime(1, 20, playthrough_id=first)
        second = self.slice.create_playthrough()
        self.slice.add_playtime(2, 0, playthrough_id=second)
        third = self.slice.create_playthrough()
        state = self.slice.load_detail()
        view = JourneyView()

        view.set_presentation(JourneyPresentationBuilder().build(
            state, playthrough_id=third
        ))
        self.assertEqual(view.run_kind.text(), "Текущее")
        self.assertNotIn("time", view.run_metrics)
        view.set_presentation(JourneyPresentationBuilder().build(
            state, playthrough_id=first
        ))
        self.assertEqual(view.run_kind.text(), "Первое прохождение")
        view.set_presentation(JourneyPresentationBuilder().build(
            state, playthrough_id=second
        ))
        self.assertEqual(view.run_kind.text(), "Повторное прохождение")


    def test_completion_pass_end_to_end_persists_after_reopen(self):
        catalog_before = self.storage.catalog_db.read_bytes()
        playthrough_id = self.slice.create_playthrough()

        self.slice.set_stage_state(
            "stage-01", "completed", playthrough_id=playthrough_id
        )
        self.slice.set_stage_rating(
            "stage-01", 3.0, playthrough_id=playthrough_id
        )
        self.slice.set_stage_mood(
            "stage-01", "happy", playthrough_id=playthrough_id
        )
        self.slice.set_stage_favorite(
            "stage-01", True, playthrough_id=playthrough_id
        )
        self.slice.set_stage_difficult(
            "stage-01", True, playthrough_id=playthrough_id
        )
        event_id = self.slice.add_timeline_event(
            "stage-01", "note", title="Первый бой", body="Черновик",
            rating_after=8.0, mood_id="neutral",
            playthrough_id=playthrough_id,
        )
        self.slice.revise_timeline_event(
            event_id, title="Первый бой", body="Обновлённая заметка",
            rating_after=9.0, mood_id="excited",
            playthrough_id=playthrough_id,
        )

        reopened = DoomVerticalSlice(
            self.storage.catalog_db, self.storage.user_db
        )
        model = JourneyPresentationBuilder().build(
            reopened.load_detail(), playthrough_id=playthrough_id
        )
        first, second = model.stages[:2]
        event = next(item for item in first.entries if item.source_id == event_id)

        self.assertEqual(first.state, "completed")
        self.assertEqual(second.state, "current")
        self.assertEqual(first.rating, 3.0)
        self.assertEqual(first.mood_id, "happy")
        self.assertTrue(first.favorite)
        self.assertTrue(first.difficult)
        self.assertEqual(event.body, "Обновлённая заметка")
        self.assertEqual((event.rating, event.mood_id), (9.0, "excited"))
        self.assertEqual(self.storage.catalog_db.read_bytes(), catalog_before)

    def test_all_supported_personal_event_types_are_projected(self):
        playthrough_id = self.slice.create_playthrough()
        event_types = (
            "note", "screenshot", "achievement", "favorite_moment",
            "music", "difficult_moment", "impression", "other",
        )
        created = {
            self.slice.add_timeline_event(
                "stage-02", event_type, title=event_type,
                playthrough_id=playthrough_id,
            ): event_type
            for event_type in event_types
        }

        model = JourneyPresentationBuilder().build(
            self.slice.load_detail(), playthrough_id=playthrough_id
        )
        projected = {
            entry.source_id: entry.kind for entry in model.stages[1].entries
            if entry.source_id in created
        }
        self.assertEqual(projected, created)

    def _create_runs(self, count: int) -> list[str]:
        return [self.slice.create_playthrough() for _ in range(count)]

    def _active_runs(self):
        with UserUnitOfWork(self.storage.user_db) as uow:
            return uow.playthroughs.list_for_item(
                self.slice.ref.source_type, self.slice.ref.item_id
            )

    def test_delete_middle_selects_previous_without_renumbering(self):
        first, middle, last = self._create_runs(3)
        selected = self.slice.delete_playthrough(middle)
        runs = self._active_runs()
        self.assertEqual(selected, first)
        self.assertEqual([run.playthrough_id for run in runs], [first, last])
        self.assertEqual([run.sequence_no for run in runs], [1, 3])
        self.assertEqual([run.is_current for run in runs], [True, False])

    def test_delete_last_selects_previous(self):
        first, second, last = self._create_runs(3)
        self.assertEqual(self.slice.delete_playthrough(last), second)
        self.assertEqual(
            [run.playthrough_id for run in self._active_runs()],
            [first, second],
        )

    def test_delete_first_selects_next(self):
        first, second, third = self._create_runs(3)
        self.assertEqual(self.slice.delete_playthrough(first), second)
        self.assertEqual(
            [run.playthrough_id for run in self._active_runs()],
            [second, third],
        )

    def test_delete_only_run_produces_empty_state(self):
        only = self.slice.create_playthrough()
        self.assertIsNone(self.slice.delete_playthrough(only))
        self.assertEqual(self._active_runs(), [])
        state = self.slice.load_detail()
        self.assertEqual(state.playthroughs, ())
        model = JourneyPresentationBuilder().build(state)
        view = JourneyView()
        view.set_presentation(model)
        self.assertTrue(view.empty_title.isVisibleTo(view))
        self.assertFalse(view.run_actions.isVisibleTo(view))

    def test_cancelled_confirmation_does_not_call_delete_service(self):
        class SliceStub:
            deleted = False

            @staticmethod
            def load_detail():
                return SimpleNamespace(
                    playthroughs=(SimpleNamespace(
                        playthrough_id="run-2", sequence_no=2
                    ),)
                )

            def delete_playthrough(self, _playthrough_id):
                self.deleted = True

        host = SimpleNamespace(
            slice=SliceStub(),
            _confirm_delete_playthrough=lambda _sequence: False,
        )
        DoomAw02Panel._request_delete_playthrough(host, "run-2")
        self.assertFalse(host.slice.deleted)

    def test_delete_isolated_to_selected_run_and_catalog_is_unchanged(self):
        first, second = self._create_runs(2)
        self.slice.add_playtime(1, 0, playthrough_id=first)
        self.slice.set_stage_state("stage-01", "completed", playthrough_id=first)
        self.slice.set_stage_mood("stage-01", "happy", playthrough_id=first)
        self.slice.add_impression(
            "Сохранить", progress_value=1, progress_unit="journey_stage",
            playthrough_id=first,
        )
        self.slice.save_personal_rating(8.0, playthrough_id=first)
        self.slice.add_playtime(2, 0, playthrough_id=second)
        self.slice.add_impression(
            "Удалить", progress_value=1, progress_unit="journey_stage",
            playthrough_id=second,
        )
        self.slice.save_personal_rating(9.0, playthrough_id=second)
        catalog_before = self.storage.catalog_db.read_bytes()

        self.slice.delete_playthrough(second)

        self.assertEqual(self.storage.catalog_db.read_bytes(), catalog_before)
        history = GamePlaythroughHistoryQueryService(
            self.storage.user_db
        ).get(self.slice.ref)
        self.assertEqual(history.playthrough_count, 1)
        self.assertEqual(history.playthroughs[0].playthrough.playthrough_id, first)
        self.assertEqual(history.total_time_all_playthroughs_minutes, 60)
        self.assertEqual([note.text for note in history.notes], ["Сохранить"])
        self.assertEqual([rating.value_tenths for rating in history.ratings], [80])
        self.assertEqual([mood.mood_id for mood in history.moods], ["happy"])

    def test_new_run_uses_max_historical_sequence_after_delete(self):
        _first, _second, third = self._create_runs(3)
        self.slice.delete_playthrough(third)
        fourth = self.slice.create_playthrough()
        runs = self._active_runs()
        self.assertEqual(runs[-1].playthrough_id, fourth)
        self.assertEqual(runs[-1].sequence_no, 4)


if __name__ == "__main__":
    unittest.main()
