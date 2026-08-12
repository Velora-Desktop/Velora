from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QSignalSpy, QTest

from app.ui.velora_ui.charts import MoodChart, MoodChartPoint
from app.ui.velora_ui.components import (
    VeloraActionCard, VeloraMoodSelector, VeloraRatingSelector,
    VeloraScrollArrow, VeloraStageCard,
)
from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.moods import MoodRegistry
from app.ui.game_detail.journey_widgets import (
    EVENT_META, JourneyActionCard, _rating_verdict,
)


class VeloraUiKitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_journey_rating_verdict_uses_stable_score_bands(self):
        self.assertEqual(_rating_verdict(9.0), "Отлично")
        self.assertEqual(_rating_verdict(7.0), "Хорошо")
        self.assertEqual(_rating_verdict(5.0), "Средне")
        self.assertEqual(_rating_verdict(3.0), "Удовлетворительно")
        self.assertEqual(_rating_verdict(2.9), "Плохо")

    def test_quick_actions_use_impression_instead_of_rating_change(self):
        actions = {kind: (icon, label) for kind, icon, label in EVENT_META}
        self.assertNotIn("rating", actions)
        self.assertEqual(
            actions["impression"], ("journey.impression", "Впечатление")
        )
        self.assertTrue(IconProvider.exists("journey.impression"))

    def test_journey_quick_action_is_large_and_horizontally_expandable(self):
        action = JourneyActionCard(
            "impression", "journey.impression", "Впечатление"
        )
        self.assertGreaterEqual(action.minimumWidth(), 128)
        self.assertEqual(action.minimumHeight(), 90)
        self.assertEqual(
            action.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Expanding,
        )
        self.assertEqual(action.icon_label.pixmap().width(), 28)

    def test_registered_icons_exist_and_missing_icon_has_safe_fallback(self):
        self.assertTrue(all(IconProvider.exists(key) for key in IconProvider.keys()))
        fallback = IconProvider.pixmap("missing.key", 20)
        self.assertFalse(fallback.isNull())
        self.assertEqual((fallback.width(), fallback.height()), (20, 20))

    def test_mood_definitions_have_unique_stable_ids_and_valid_weights(self):
        moods = MoodRegistry.all()
        self.assertEqual(len({item.id for item in moods}), len(moods))
        self.assertTrue(all(isinstance(item.score_weight, int) for item in moods))
        self.assertTrue(all(IconProvider.exists(item.icon_key) for item in moods))

    def test_mood_selector_exposes_id_not_localized_label(self):
        selector = VeloraMoodSelector()
        selector.set_mood_id("happy")
        self.assertEqual(selector.mood_id(), "happy")
        self.assertEqual(selector.currentText(), "Радость")

    def test_cards_and_chart_construct_without_database(self):
        stage = VeloraStageCard(
            "stage-1", 1, "Начало", "active", rating=8.0, event_count=10
        )
        action = VeloraActionCard("note", "journey.note", "Заметка")
        chart = MoodChart()
        chart.set_points((MoodChartPoint(1, "happy", 8.0, True),))
        self.assertEqual(stage.stage_id, "stage-1")
        self.assertEqual(stage.event_count_label.text(), "Событий: 10")
        self.assertEqual(action.action_id, "note")
        self.assertEqual(chart.points[0].mood_id, "happy")

    def test_ui_kit_has_no_storage_or_application_imports(self):
        forbidden = ("app.storage", "app.application", "sqlite3")
        for path in Path("app/ui/velora_ui").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
            self.assertFalse(any(name.startswith(forbidden) for name in imported), path)

    def test_mood_chart_accepts_empty_data(self):
        chart = MoodChart()
        chart.set_points(())
        self.assertEqual(chart.points, ())

    def test_mood_chart_keeps_rated_events_between_stage_points(self):
        chart = MoodChart()
        chart.set_points((
            MoodChartPoint(1, rating=8.0, label="01"),
            MoodChartPoint(1, rating=6.0, label="Событие", is_event=True),
            MoodChartPoint(2, rating=9.0, label="02"),
        ))
        self.assertEqual(len(chart.points), 3)
        self.assertTrue(chart.points[1].is_event)
        self.assertEqual(chart.points[1].rating, 6.0)

    def test_mood_chart_colors_rating_dynamics(self):
        low = MoodChartPoint(1, rating=4.0)
        high = MoodChartPoint(1, rating=8.0, is_event=True)
        similar = MoodChartPoint(2, rating=8.1)
        self.assertEqual(MoodChart.trend_color(low, high), "#20C875")
        self.assertEqual(MoodChart.trend_color(high, low), "#E04B4B")
        self.assertEqual(MoodChart.trend_color(high, similar), "#A33CFF")
        unrated = MoodChartPoint(3)
        self.assertEqual(MoodChart.trend_color(similar, unrated), "#56616C")
        self.assertEqual(MoodChart.rating_position(unrated), 0.0)
        self.assertGreater(MoodChart.rating_position(high), 0.0)

    def test_mood_chart_stage_axis_excludes_event_labels(self):
        chart = MoodChart()
        chart.set_points((
            MoodChartPoint(1, rating=7.0, label="01"),
            MoodChartPoint(1, rating=8.0, label="Заметка", is_event=True),
            MoodChartPoint(2, rating=9.0, label="02"),
        ))
        mission_labels = tuple(
            point.label for point in chart.points if not point.is_event
        )
        self.assertEqual(mission_labels, ("01", "02"))

    def test_rating_selector_exposes_value_without_spinbox_controls(self):
        selector = VeloraRatingSelector()
        self.assertLessEqual(selector.width(), 650)
        self.assertEqual(selector.height(), 72)
        self.assertTrue(
            all(button.size().width() == 60 and button.size().height() == 60
                for button in selector._buttons)
        )
        self.assertEqual(len({button.styleSheet() for button in selector._buttons}), 10)
        selector.setValue(8)
        self.assertEqual(selector.value(), 8.0)
        selector.clear()
        self.assertIsNone(selector.value())

    def test_scroll_arrow_supports_hold_navigation(self):
        arrow = VeloraScrollArrow("right")
        self.assertTrue(arrow.autoRepeat())
        self.assertGreater(arrow.autoRepeatDelay(), arrow.autoRepeatInterval())

    def test_stage_card_hit_zones_have_independent_actions(self):
        card = VeloraStageCard("stage-1", 1, "Начало", "active", rating=8.0)
        card.show()
        selected = QSignalSpy(card.stage_selected)
        opened = QSignalSpy(card.stage_open_requested)
        statuses = QSignalSpy(card.status_toggled)
        favorites = QSignalSpy(card.favorite_toggled)

        QTest.mouseClick(card, Qt.MouseButton.LeftButton, pos=QPoint(90, 60))
        self.assertEqual(selected.count(), 1)
        self.assertEqual(statuses.count(), 0)

        QTest.mouseClick(card.status_icon, Qt.MouseButton.LeftButton)
        self.assertEqual(statuses.count(), 1)
        self.assertTrue(statuses.at(0)[1])
        self.assertEqual(selected.count(), 1)

        QTest.mouseClick(card.favorite_button, Qt.MouseButton.LeftButton)
        self.assertEqual(favorites.count(), 1)
        self.assertEqual(selected.count(), 1)
        self.assertEqual(statuses.count(), 1)

        QTest.mouseDClick(card, Qt.MouseButton.LeftButton, pos=QPoint(90, 60))
        self.assertEqual(opened.count(), 1)
        self.assertEqual(statuses.count(), 1)
        self.assertTrue(all(
            label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            for label in card.findChildren(QLabel)
        ))

    def test_completed_stage_status_button_returns_stage_to_current(self):
        card = VeloraStageCard("stage-1", 1, "Начало", "complete")
        statuses = QSignalSpy(card.status_toggled)
        QTest.mouseClick(card.status_icon, Qt.MouseButton.LeftButton)
        self.assertEqual(statuses.count(), 1)
        self.assertFalse(statuses.at(0)[1])


if __name__ == "__main__":
    unittest.main()
