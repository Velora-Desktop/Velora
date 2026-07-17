import unittest
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.core.icon_registry import IconRegistry
from app.core.platforms import sorted_platforms
from app.models.game import MEDIA_STATUSES
from app.models.game import GameData
from app.ui.profile.statistics_dashboard import StatisticsDashboard
from app.services.age_filter_service import AgeFilterService


class Aw008StructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
    def test_platforms_follow_canonical_order(self) -> None:
        values = sorted_platforms(["Android", "PS5", "Linux", "PC", "Xbox", "iOS", "Other"])
        self.assertEqual(values, ["PC", "PS5", "Xbox", "Linux", "Android", "iOS", "Other"])

    def test_v2_icons_and_fallback_are_available(self) -> None:
        self.assertIsNotNone(IconRegistry.path("playtime", category="metrics"))
        self.assertIsNotNone(IconRegistry.path("database_check", category="diagnostics"))
        self.assertIsNone(IconRegistry.path("not-a-real-aw008-icon"))

    def test_each_media_type_has_its_own_statuses(self) -> None:
        self.assertIn("ПРОШЁЛ", MEDIA_STATUSES["Игры"])
        self.assertIn("ПОСМОТРЕЛ", MEDIA_STATUSES["Фильмы"])
        self.assertIn("ЖДУ НОВЫЙ СЕЗОН", MEDIA_STATUSES["Сериалы"])
        self.assertIn("ОТКАЗАЛСЯ", MEDIA_STATUSES["Программы"])

    def test_statistics_use_only_personal_interactions(self) -> None:
        untouched = GameData("Untouched", "9.0", "—", "НЕ НАЧИНАЛ", "Dev", "2020", "PC", "1P")
        rated = GameData("Rated", "8.0", "7.0", "ПРОШЁЛ", "Dev", "2021", "PC", "1P", user_interacted=True)
        rated.playtime_hours = 3.5
        dashboard = StatisticsDashboard(); dashboard.refresh([untouched, rated]); self.app.processEvents()
        self.assertEqual(dashboard.cards["objects"].value.text(), "1")
        self.assertEqual(dashboard.cards["rated"].value.text(), "1")
        platform_icons = [
            label for label in dashboard.platforms.values.findChildren(QLabel)
            if label.pixmap() and not label.pixmap().isNull()
        ]
        self.assertTrue(platform_icons)
        self.assertTrue(dashboard.category_stats.values.findChildren(QLabel))
        self.assertTrue(dashboard.library_progress.values.findChildren(QLabel))
        self.assertEqual(dashboard.cards["hours"].value.text(), "3.5 ч")

    def test_age_filter_accepts_catalog_age_values(self) -> None:
        self.assertTrue(AgeFilterService.is_visible(16, True))
        self.assertFalse(AgeFilterService.is_visible(18, True))
        self.assertTrue(AgeFilterService.is_visible(18, False))
        adult = GameData("Adult", "8.0", "—", "НЕ НАЧИНАЛ", "Dev", "2020", "PC", "1P", age_rating=18)
        self.assertFalse(AgeFilterService.is_visible(adult, True))
        self.assertFalse(AgeFilterService.is_visible("18+", True))


if __name__ == "__main__":
    unittest.main()
