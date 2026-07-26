import tempfile
import unittest
from pathlib import Path

from app.data.user_repository import UserRepository
from app.models.game import GameData
from app.models.personal_library import SmartListDefinition, UserGoal
from app.services.smart_list_service import SmartListService
from app.services.taste_analytics_service import TasteAnalyticsService


def item(**values):
    defaults = dict(title="Test", general_score="8.0", personal_score="—", status="НЕ НАЧИНАЛ", developer="Dev", year="2020", platform="PC", mode="1P", catalog_id="g-test-001")
    defaults.update(values)
    return GameData(**defaults)


class Aw009SmartLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repository = UserRepository(Path(self.temp.name) / "user.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_migration_creates_aw009_tables(self):
        import sqlite3
        connection = sqlite3.connect(self.repository.path)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            version = connection.execute("SELECT 1 FROM schema_migrations WHERE version='006'").fetchone()
        finally:
            connection.close()
        self.assertTrue({"smart_lists", "user_notes", "user_tags", "user_item_tags", "user_goals", "interaction_sessions"}.issubset(tables))
        self.assertIsNotNone(version)

    def test_smart_lists_use_live_items(self):
        values = [item(), item(title="Rated", catalog_id="g-test-002", personal_score="9.2", favorite=True, user_interacted=True)]
        high = next(value for value in SmartListService.BUILT_INS if value.name == "Оценка 9 и выше")
        self.assertEqual(["Rated"], [value.title for value in SmartListService.filter(values, high)])

    def test_repository_persists_lists_tags_goals_notes_and_repeats(self):
        definition = SmartListDefinition(None, "Любимое", "Игры", {"favorite": True})
        list_id = self.repository.save_smart_list(definition)
        tag_id = self.repository.add_tag("уютное")
        self.repository.assign_tag("g-test-001", tag_id)
        self.repository.save_note("g-test-001", "Личная заметка")
        goal_id = self.repository.save_goal(UserGoal(None, "10 объектов", "objects", 10))
        self.repository.add_interaction_session("g-test-001", "replay", 2.5)
        self.assertEqual(list_id, self.repository.smart_lists()[0].list_id)
        self.assertEqual("уютное", self.repository.tags()[0][1])
        self.assertEqual(goal_id, self.repository.goals()[0].goal_id)
        self.assertTrue(any(row["event_type"] == "repeat" for row in self.repository.all_activity()))

    def test_taste_comparison(self):
        result = TasteAnalyticsService.score_comparison([item(personal_score="9.0"), item(catalog_id="2", personal_score="7.0", general_score="8.0")])
        self.assertEqual(100.0, result["agreement"])
        self.assertAlmostEqual(0.0, result["average_delta"])


if __name__ == "__main__":
    unittest.main()
