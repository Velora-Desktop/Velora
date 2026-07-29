from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app.models.game import GAME_STATUSES, GameData
from app.ui.catalog.game_row import GameRow
from app.ui.catalog.status_menu import StatusButton


def _game(title: str = "Doom Eternal") -> GameData:
    return GameData(
        title=title,
        general_score="8.8",
        personal_score="—",
        status=GAME_STATUSES[0],
        developer="id Software",
        year="2020",
        platform="PC",
        mode="1P",
        age_rating=18,
    )


class StatusControlStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        self.app.processEvents()

    def test_status_stress_reuses_widget_layout_menu_and_stylesheet(self):
        row = GameRow(_game())
        row.show()
        self.app.processEvents()
        button = row.status_button
        menu = button.menu()
        stylesheet = button.styleSheet()
        layout_count = row.layout().count()

        for index in range(128):
            row.set_status(GAME_STATUSES[index % len(GAME_STATUSES)], False)
            if index % 8 == 0:
                row.resize(1800 - index, 49)
                self.app.processEvents()

        self.assertIs(row.status_button, button)
        self.assertIs(row.status_button.menu(), menu)
        self.assertEqual(row.layout().count(), layout_count)
        self.assertEqual(row.status_button.styleSheet(), stylesheet)
        self.assertTrue(row.status_button.isVisible())
        row.deleteLater()

    def test_selected_and_hover_surfaces_remain_owned_by_row(self):
        row = GameRow(_game())
        title_style = row.title_button.styleSheet()
        score_style = row.personal_score_label.styleSheet()
        for selected in (True, False, True, False):
            row.set_selected(selected)
        self.assertEqual(row.title_button.styleSheet(), title_style)
        self.assertEqual(row.personal_score_label.styleSheet(), score_style)
        self.assertIn("background:transparent", title_style)
        self.assertIn("background:transparent", score_style)
        self.assertIsInstance(row.title_button, QLabel)
        self.assertNotIsInstance(row.title_button, QPushButton)
        self.assertFalse(
            row.title_button.testAttribute(
                Qt.WidgetAttribute.WA_OpaquePaintEvent
            )
        )
        row.deleteLater()

    def test_menu_selection_and_theme_refresh_keep_same_control(self):
        selected: list[str] = []
        button = StatusButton(selected.append)
        button.set_status(GAME_STATUSES[0])
        identity = id(button)
        stylesheet = button.styleSheet()
        old_application_style = self.app.styleSheet()
        try:
            keyboard_target = button.menu().actions()[0].defaultWidget()
            keyboard_target.show()
            keyboard_target.setFocus()
            QTest.keyClick(keyboard_target, Qt.Key.Key_Space)
            for cycle in range(24):
                widget_action = button.menu().actions()[cycle % len(GAME_STATUSES)]
                QTest.mouseClick(
                    widget_action.defaultWidget(),
                    Qt.MouseButton.LeftButton,
                )
                self.app.setStyleSheet(
                    "QWidget { color:#F1F2F4; }" if cycle % 2 else ""
                )
                self.app.processEvents()
            self.assertEqual(id(button), identity)
            self.assertEqual(button.styleSheet(), stylesheet)
            self.assertEqual(len(selected), 25)
        finally:
            self.app.setStyleSheet(old_application_style)
            button.deleteLater()

    def test_reopening_other_game_does_not_share_status_state(self):
        first = GameRow(_game())
        second = GameRow(_game("Half-Life 2"))
        first.set_status(GAME_STATUSES[1], False)
        second.set_status(GAME_STATUSES[2], False)
        self.assertEqual(first.status_button.status_value, GAME_STATUSES[1])
        self.assertEqual(second.status_button.status_value, GAME_STATUSES[2])
        self.assertIsNot(first.status_button, second.status_button)
        first.deleteLater()
        second.deleteLater()


if __name__ == "__main__":
    unittest.main()
