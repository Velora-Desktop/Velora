import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from PySide6.QtCore import QDateTime, QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app.application.creator_sources import CreatorSourceBuilder
from app.application.doom_vertical_slice import (
    DoomDetailState, ImpressionSummary, JourneySummary, PlaythroughSummary,
    RatingSummary,
)
from app.application.game_row_contracts import GameRowDto, RowSelectionIdentity
from app.application.journey_presentation import JourneyPresentationBuilder
from app.application.journey_templates import JourneyTemplateRegistry
from app.ui.game_detail.journey_widgets import (
    JourneyEntryDialog, JourneyQuickEditor, JourneyView,
)
from app.ui.game_detail.doom_aw02_panel import DoomAw02Panel
from velora_contracts.enums import LibraryMembershipState, SourceType
from velora_contracts.value_objects import CatalogItemRef


def make_state():
    ref = CatalogItemRef(SourceType.OFFICIAL, "9df7cc01-d487-4cd7-814d-e70ec7967a4a")
    row = GameRowDto(
        RowSelectionIdentity.from_ref(ref), ref, "u1", "Doom Eternal",
        LibraryMembershipState.ACTIVE, "p1", "playing", 180, "middle", 85,
        "Сильный темп", "2026-07-29T10:00:00",
    )
    return DoomDetailState(
        row, "Описание", (),
        (PlaythroughSummary("p1", 1, "playing", "2026-07-01", None, 180, "middle", None),),
        (ImpressionSummary("Сильный темп", "middle", 1, 180, "2026-07-02T10:00:00"),),
        (RatingSummary("checkpoint", 85, "middle", 1, "Поворот", True, "2026-07-02T11:00:00"),),
        (JourneySummary("Начато прохождение", "", 1, "2026-07-01T10:00:00"),
         JourneySummary("Создана контрольная точка", "Середина", 1, "2026-07-02T10:00:00")),
    )


class JourneyTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_registry_contains_all_required_templates(self):
        self.assertEqual(len(JourneyTemplateRegistry().all()), 21)

    def test_doom_is_composed_not_a_separate_backend(self):
        template = JourneyTemplateRegistry().doom_eternal()
        self.assertEqual(template.base_structure, "timeline")
        self.assertIn("arena_shooter", template.modifiers)

    def test_official_studio_payload_controls_structure_only(self):
        payload = {
            "payload_version": 1,
            "template_id": "story_campaign",
            "name": "Моя официальная кампания",
            "stages": [
                {"title": "Пролог", "visible": True},
                {"title": "Скрытый этап", "visible": False},
                {"title": "Финал", "visible": True},
            ],
            "optional_blocks": ["ratings", "notes"],
            "quick_editor_fields": ["Статус", "Впечатление"],
        }
        template = JourneyTemplateRegistry().from_payload(payload)
        self.assertEqual(template.stage_titles, ("Пролог", "Финал"))
        self.assertNotIn("impressions", payload)
        self.assertNotIn("screenshots", payload)

    def test_builder_maps_existing_state_and_order(self):
        model = JourneyPresentationBuilder().build(make_state())
        self.assertEqual(model.game_title, "Doom Eternal")
        self.assertEqual(model.playthrough_sequence, 1)
        self.assertEqual(model.total_playtime_minutes, 180)
        self.assertTrue(model.all_sources)
        self.assertEqual(len(model.stages), 13)
        self.assertEqual(model.stages[0].title, "Ад на Земле")
        self.assertEqual(model.stages[-1].title, "Последний грех")

    def test_optional_data_can_be_empty(self):
        state = make_state()
        model = JourneyPresentationBuilder().build(replace(
            state, playthroughs=(), impressions=(), ratings=(), journey=()
        ))
        self.assertIsNone(model.playthrough_id)
        self.assertEqual(model.all_sources, ())

    def test_creator_sources_are_automatic_and_stable(self):
        journey = JourneyPresentationBuilder().build(make_state())
        first = CreatorSourceBuilder().build(journey)
        source_id = first.sources[0].source_id
        second = CreatorSourceBuilder().build(journey)
        self.assertEqual(source_id, second.sources[0].source_id)
        self.assertTrue(any(item.source_id == source_id for item in second.selected_sources))
        self.assertEqual(second.selected_sources, second.sources)

    def test_journey_view_has_one_controlled_horizontal_timeline(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        self.assertEqual(len(view._stage_buttons), 13)
        self.assertTrue(view._selected_stage_id.startswith("stage-"))
        self.assertEqual(
            view.timeline_scroll.verticalScrollBarPolicy(),
            view.timeline_scroll.verticalScrollBarPolicy().ScrollBarAlwaysOff,
        )
        self.assertFalse(any(
            "ВИД:" in button.text().upper()
            for button in view.findChildren(QPushButton)
        ))

    def test_journey_selector_supports_ten_playthroughs(self):
        state = make_state()
        runs = tuple(
            replace(state.playthroughs[0], playthrough_id=f"p{number}",
                    sequence_no=number)
            for number in range(1, 11)
        )
        view = JourneyView()
        view.set_presentation(
            JourneyPresentationBuilder().build(
                replace(state, playthroughs=runs),
                playthrough_sequence=10,
            )
        )
        self.assertEqual(view.run_selector.count(), 10)
        self.assertEqual(view.run_selector.currentData(), "p10")
        self.assertEqual(view.run_selector.maxVisibleItems(), 10)

    def test_journey_selector_scrolls_after_ten_playthroughs(self):
        state = make_state()
        runs = tuple(
            replace(
                state.playthroughs[0],
                playthrough_id=f"p{number}",
                sequence_no=number,
            )
            for number in range(1, 12)
        )
        view = JourneyView()
        view.set_presentation(
            JourneyPresentationBuilder().build(
                replace(state, playthroughs=runs),
                playthrough_id="p11",
            )
        )
        self.assertEqual(view.run_selector.count(), 11)
        self.assertEqual(view.run_selector.maxVisibleItems(), 10)
        self.assertEqual(view.run_selector.currentText(), "ПРОХОЖДЕНИЕ №11")
        self.assertEqual(
            view.run_selector.view().verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )

    def test_journey_selector_uses_contiguous_visible_numbers(self):
        state = make_state()
        runs = tuple(
            replace(
                state.playthroughs[0],
                playthrough_id=playthrough_id,
                sequence_no=sequence_no,
            )
            for playthrough_id, sequence_no in (("p1", 1), ("p2", 2), ("p10", 10))
        )
        view = JourneyView()
        view.set_presentation(
            JourneyPresentationBuilder().build(
                replace(state, playthroughs=runs),
                playthrough_id="p10",
            )
        )
        self.assertEqual(
            [view.run_selector.itemText(index) for index in range(3)],
            ["ПРОХОЖДЕНИЕ №1", "ПРОХОЖДЕНИЕ №2", "ПРОХОЖДЕНИЕ №3"],
        )
        self.assertEqual(view.run_selector.currentData(), "p10")

    def test_route_scroll_position_survives_refresh(self):
        view = JourneyView()
        view.resize(900, 700)
        model = JourneyPresentationBuilder().build(make_state())
        view.set_presentation(model)
        view.show()
        QApplication.processEvents()
        bar = view.timeline_scroll.horizontalScrollBar()
        bar.setValue(min(250, bar.maximum()))
        expected = bar.value()
        view.set_presentation(model)
        QApplication.processEvents()
        self.assertEqual(bar.value(), expected)

    def test_route_arrows_follow_scroll_boundaries(self):
        view = JourneyView()
        view.resize(900, 700)
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        view.show()
        QApplication.processEvents()
        bar = view.timeline_scroll.horizontalScrollBar()
        self.assertGreater(bar.maximum(), bar.minimum())
        bar.setValue(bar.minimum())
        QApplication.processEvents()
        self.assertFalse(view.route_previous.isVisible())
        self.assertTrue(view.route_next.isVisible())
        bar.setValue(bar.maximum())
        QApplication.processEvents()
        self.assertTrue(view.route_previous.isVisible())
        self.assertFalse(view.route_next.isVisible())

    def test_journey_uses_page_scroll_in_compact_window(self):
        view = JourneyView()
        view.resize(1366, 768)
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        view.show()
        QApplication.processEvents()
        self.assertIsNone(view.page_scroll)

    def test_pixel_match_components_keep_semantic_minimum_sizes(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        first = next(iter(view._stage_buttons.values()))
        self.assertGreaterEqual(first.width(), 185)
        self.assertGreaterEqual(first.height(), 120)
        # The compact reference card keeps all controls visible without the
        # oversized empty vertical area used by the first Journey pass, while
        # retaining enough height for event rating and mood metadata.
        self.assertGreaterEqual(view.detail.height(), 180)
        self.assertLessEqual(view.detail.height(), 275)
        self.assertGreaterEqual(view.analytics.height(), 115)
        self.assertLessEqual(view.analytics.height(), 195)
        self.assertLessEqual(view.route_previous.height(), 52)

    def test_journey_mood_graph_keeps_rating_separate_from_explicit_mood(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        self.assertEqual(len(view.graph.points), 13)
        self.assertTrue(all(point.mood_id is None for point in view.graph.points))
        self.assertTrue(any(point.rating == 8.5 for point in view.graph.points))

    def test_journey_stage_selection_updates_without_rebuilding_view(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        original = id(view)
        view._select_stage("stage-01")
        self.assertEqual(id(view), original)
        self.assertEqual(view._selected_stage_id, "stage-01")
        self.assertTrue(view._stage_buttons["stage-01"].isChecked())

    def test_event_editor_separates_date_and_scrollable_time(self):
        stage = JourneyPresentationBuilder().build(make_state()).stages[0]
        dialog = JourneyEntryDialog(stage, "note", 1)
        self.assertEqual(dialog.event_date.displayFormat(), "dd.MM.yyyy")
        self.assertTrue(dialog.event_date.calendarPopup())
        self.assertIn("QDateEdit::drop-down{background:transparent", dialog.styleSheet())
        self.assertEqual(dialog.event_time.displayFormat(), "HH:mm")
        self.assertTrue(dialog.event_time.wrapping())
        dialog.event_date.setDate(QDateTime.fromString(
            "2026-08-04T12:02:00", Qt.DateFormat.ISODate
        ).date())
        dialog.event_time.setTime(QDateTime.fromString(
            "2026-08-04T12:02:00", Qt.DateFormat.ISODate
        ).time())
        self.assertEqual(dialog.draft().occurred_at, "2026-08-04T12:02:00")

    def test_stage_tile_double_click_opens_entry_type_menu(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        view.show()
        QApplication.processEvents()
        card = view._stage_buttons["stage-01"]
        QTest.mouseDClick(
            card, Qt.MouseButton.LeftButton, pos=QPoint(90, 72)
        )
        QApplication.processEvents()
        self.assertTrue(view._entry_type_menu.isVisible())
        actions = view._entry_type_menu.actions()
        self.assertEqual(actions[0].text(), "Уточнить состояние")
        self.assertIsNotNone(actions[0].menu())
        self.assertTrue(actions[1].isSeparator())
        self.assertGreaterEqual(len(actions), 10)
        view._entry_type_menu.close()

    def test_stage_state_submenu_emits_existing_state_request(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        requested: list[tuple[str, str]] = []
        view.stage_state_requested.connect(
            lambda stage_id, state: requested.append((stage_id, state))
        )

        view._open_stage_dialog("stage-01")
        state_menu = view._stage_state_menu
        self.assertIsNotNone(state_menu)
        completed = next(
            action for action in state_menu.actions()
            if action.text() == "Завершено"
        )
        completed.trigger()

        self.assertEqual(requested, [("stage-01", "completed")])
        view._entry_type_menu.close()

    def test_journey_has_no_manual_creator_actions(self):
        model = JourneyPresentationBuilder().build(make_state())
        view = JourneyView()
        view.set_presentation(model)
        self.assertFalse(any(
            "CREATOR" in button.text().upper()
            for button in view.findChildren(QPushButton)
        ))

    @unittest.skip("AW0.23 compact Journey uses direct rating and modal entries")
    def test_quick_editor_emits_selected_stage_payload(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        view._select_stage("stage-02")
        QApplication.processEvents()
        editor = view.findChild(JourneyQuickEditor)
        payloads = []
        view.quick_save_requested.connect(lambda *args: payloads.append(args))
        editor.status.setCurrentIndex(editor.status.findData("playing"))
        editor.rating.setValue(7.4)
        editor.impression.setText("Сражения стали заметно динамичнее")
        editor._emit_save()
        self.assertEqual(payloads[0][0], "stage-02")
        self.assertEqual(payloads[0][1], "playing")
        self.assertEqual(payloads[0][2], 7.4)

    def test_quick_editor_uses_reusable_one_to_ten_rating_selector(self):
        editor = JourneyQuickEditor()
        labels = {button.text() for button in editor.findChildren(QPushButton)}
        self.assertTrue({str(value) for value in range(1, 11)}.issubset(labels))

    def test_stage_bound_impression_maps_to_exact_stage(self):
        state = make_state()
        impression = ImpressionSummary(
            "Арена запомнилась",
            None,
            1,
            200,
            "2026-07-02T12:00:00",
            5.0,
            "journey_stage",
        )
        model = JourneyPresentationBuilder().build(
            replace(state, impressions=(impression,))
        )
        self.assertTrue(any(
            entry.kind == "impression" and entry.body == "Арена запомнилась"
            for entry in model.stages[4].entries
        ))
        self.assertFalse(any(
            entry.kind == "impression"
            for index, stage in enumerate(model.stages)
            if index != 4
            for entry in stage.entries
        ))

    def test_completed_route_fills_every_stage(self):
        state = make_state()
        row = replace(state.row, playthrough_status="completed")
        run = replace(state.playthroughs[0], status="completed")
        model = JourneyPresentationBuilder().build(
            replace(state, row=row, playthroughs=(run,))
        )
        completed = JourneyView._completed_stage_ids(
            model.stages, model.status
        )
        self.assertEqual(len(completed), 13)

    def test_switching_playthrough_keeps_histories_separate(self):
        state = make_state()
        old_run = replace(
            state.playthroughs[0],
            playthrough_id="p0",
            sequence_no=1,
            status="completed",
        )
        new_run = replace(
            state.playthroughs[0],
            playthrough_id="p2",
            sequence_no=2,
            status="playing",
        )
        impression = replace(
            state.impressions[0], playthrough_sequence=2
        )
        model = JourneyPresentationBuilder().build(
            replace(
                state,
                playthroughs=(old_run, new_run),
                impressions=(impression,),
            ),
            playthrough_sequence=1,
        )
        self.assertEqual(model.playthrough_sequence, 1)
        self.assertEqual(model.impressions, ())

    def test_journey_switches_stages_repeatedly_without_replacing_view(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        identity = id(view)
        detail_identity = id(view.detail)
        for index in range(120):
            view._select_stage(f"stage-{(index % 13) + 1:02d}")
            QApplication.processEvents()
        self.assertEqual(id(view), identity)
        self.assertEqual(id(view.detail), detail_identity)
        self.assertEqual(view._selected_stage_id, "stage-03")

    def test_playthrough_selector_emits_identity_without_persistence(self):
        state = make_state()
        second = replace(
            state.playthroughs[0],
            playthrough_id="p2",
            sequence_no=2,
        )
        model = JourneyPresentationBuilder().build(
            replace(state, playthroughs=(state.playthroughs[0], second)),
            playthrough_sequence=1,
        )
        view = JourneyView()
        values = []
        view.playthrough_selection_requested.connect(values.append)
        view.set_presentation(model)
        view.run_selector.setCurrentIndex(1)
        self.assertEqual(values, ["p2"])
        self.assertEqual(model.playthrough_sequence, 1)

    def test_panel_opens_latest_playthrough_editable_and_numbered(self):
        state = make_state()
        old_run = replace(
            state.playthroughs[0],
            playthrough_id="p1",
            sequence_no=1,
            status="completed",
        )
        latest_run = replace(
            state.playthroughs[0],
            playthrough_id="p10",
            sequence_no=10,
            status="completed",
        )
        row = replace(
            state.row,
            current_playthrough_id="p10",
            playthrough_status="completed",
        )
        panel = DoomAw02Panel()
        panel._render(replace(
            state, row=row, playthroughs=(old_run, latest_run),
        ))
        self.assertEqual(panel.journey_page.run_selector.currentData(), "p10")
        self.assertEqual(
            panel.journey_page.run_selector.currentText(),
            "ПРОХОЖДЕНИЕ №2",
        )
        self.assertTrue(panel.journey_page.stage_rating.isEnabled())

    def test_saving_stage_memory_does_not_rewrite_playthrough_status(self):
        panel = DoomAw02Panel()
        panel._render(make_state())
        service = Mock()
        panel.slice = service
        with patch.object(panel, "refresh", return_value=None):
            panel._save_stage(
                "stage-01", "completed", 8.4, "Сильное начало", None
            )
        service.set_status.assert_not_called()
        service.save_checkpoint.assert_called_once()
        service.add_impression.assert_called_once()
        service.set_stage_mood.assert_called_once_with(
            "stage-01", None, playthrough_id="p1"
        )

    def test_journey_route_has_arrow_navigation_and_smooth_scroll(self):
        view = JourneyView()
        view.resize(1200, 700)
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        view.show()
        QApplication.processEvents()
        view.route_next.click()
        self.assertIsNotNone(view._scroll_animation)
        self.assertEqual(view._scroll_animation.duration(), 220)
        view.close()

    @unittest.skip("AW0.23 compact Journey opens the shared modal editor")
    def test_quick_event_card_only_prepares_local_impression(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        view.quick_editor.prepare_event("Скриншот")
        self.assertEqual(
            view.quick_editor.impression.toPlainText(), "Скриншот: "
        )
        self.assertFalse(view.quick_editor.impression.isReadOnly())


if __name__ == "__main__":
    unittest.main()
