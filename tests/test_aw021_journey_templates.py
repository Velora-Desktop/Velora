import unittest
from dataclasses import replace

from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QPushButton

from app.application.creator_sources import CreatorSourceBuilder
from app.application.doom_vertical_slice import (
    DoomDetailState, ImpressionSummary, JourneySummary, PlaythroughSummary,
    RatingSummary,
)
from app.application.game_row_contracts import GameRowDto, RowSelectionIdentity
from app.application.journey_presentation import JourneyPresentationBuilder
from app.application.journey_templates import JourneyTemplateRegistry
from app.ui.game_detail.journey_widgets import JourneyQuickEditor, JourneyView
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

    def test_journey_stage_selection_updates_without_rebuilding_view(self):
        view = JourneyView()
        view.set_presentation(JourneyPresentationBuilder().build(make_state()))
        original = id(view)
        view._select_stage("stage-01")
        self.assertEqual(id(view), original)
        self.assertEqual(view._selected_stage_id, "stage-01")
        self.assertTrue(view._stage_buttons["stage-01"].isChecked())

    def test_journey_has_no_manual_creator_actions(self):
        model = JourneyPresentationBuilder().build(make_state())
        view = JourneyView()
        view.set_presentation(model)
        self.assertFalse(any(
            "CREATOR" in button.text().upper()
            for button in view.findChildren(QPushButton)
        ))

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

    def test_quick_editor_uses_explicit_step_controls(self):
        editor = JourneyQuickEditor()
        self.assertEqual(
            editor.rating.buttonSymbols(),
            QAbstractSpinBox.ButtonSymbols.NoButtons,
        )
        labels = {button.text() for button in editor.findChildren(QPushButton)}
        self.assertIn("−", labels)
        self.assertIn("+", labels)

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


if __name__ == "__main__":
    unittest.main()
