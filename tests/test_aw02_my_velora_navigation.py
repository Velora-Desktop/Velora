import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.data.user_repository import UserRepository
from app.ui.profile.profile_page import ProfilePage


class MyVeloraNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_compact_top_level_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            page = ProfilePage(UserRepository(Path(directory) / "user.db"))
            self.assertEqual(
                [page.tabs.tabText(index) for index in range(page.tabs.count())],
                ["ОБЗОР", "АССИСТЕНТ", "CREATOR", "МОИ ОЦЕНКИ", "ИЗБРАННОЕ", "СТАТИСТИКА"],
            )
            self.assertEqual(
                [page.assistant.tabs.tabText(index) for index in range(page.assistant.tabs.count())],
                ["ПОМОЩНИК", "УМНЫЕ СПИСКИ", "ЦЕЛИ", "ТЕГИ", "АНАЛИТИКА ВКУСА"],
            )

    def test_taste_mode_is_explicit_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            page = ProfilePage(UserRepository(Path(directory) / "user.db"))
            page.refresh([])
            page.planning.use_taste_profile.setChecked(True)
            page.planning._random_choice()
            self.assertIn("нет объектов", page.planning.choice_result.text().casefold())


if __name__ == "__main__":
    unittest.main()
