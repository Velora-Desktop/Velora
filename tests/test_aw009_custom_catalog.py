import tempfile
import unittest
from pathlib import Path

from app.data.custom_catalog_repository import CustomCatalogRepository
from app.data.user_repository import UserRepository


class Aw009CustomCatalogTests(unittest.TestCase):
    def test_local_card_is_kept_in_user_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"user.db"; UserRepository(path); repository=CustomCatalogRepository(path)
            catalog_id=repository.save_item("Футбол","Клубы","АПЛ","Челси",creator="Chelsea FC")
            self.assertTrue(catalog_id.startswith("u-"))
            self.assertEqual(repository.sections()[0]["name"],"Футбол")
            item=repository.items()[0]
            self.assertEqual((item.media_type,item.category,item.subgroup,item.title),("Футбол","Клубы","АПЛ","Челси"))
            self.assertEqual(item.source_type,"custom")

    def test_profile_reset_removes_custom_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"user.db"; user=UserRepository(path); repository=CustomCatalogRepository(path)
            repository.save_item("Футбол","Клубы","АПЛ","Челси")
            user.reset_local_profile()
            self.assertEqual(repository.items(),[])
            self.assertEqual(repository.sections(),[])

    def test_sections_branches_and_cards_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user.db"
            UserRepository(path)
            repository = CustomCatalogRepository(path)
            repository.save_section("Футбол")
            repository.save_branch("Футбол", "Клубы", "АПЛ")
            self.assertEqual(
                repository.branches("Футбол"),
                [{"category": "Клубы", "subgroup": "АПЛ", "position": 1}],
            )
            self.assertEqual(repository.items(), [])
            catalog_id = repository.save_item("Футбол", "Клубы", "АПЛ", "Челси")
            self.assertTrue(catalog_id.startswith("u-"))
            self.assertEqual(len(repository.items()), 1)
            self.assertTrue(repository.delete_section("Футбол"))
            self.assertEqual(repository.sections(), [])
            self.assertEqual(repository.items(), [])

    def test_local_card_can_extend_official_media_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user.db"
            UserRepository(path)
            repository = CustomCatalogRepository(path)
            repository.save_branch("Игры", "Инди", "Головоломки")
            catalog_id = repository.save_item(
                "Игры", "Инди", "Головоломки", "Моя локальная игра"
            )
            item = next(value for value in repository.items() if value.catalog_id == catalog_id)
            self.assertEqual(item.media_type, "Игры")
            self.assertEqual((item.category, item.subgroup), ("Инди", "Головоломки"))

    def test_section_can_be_renamed_without_losing_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "user.db"
            UserRepository(path)
            repository = CustomCatalogRepository(path)
            catalog_id = repository.save_item(
                "Футбол", "Клубы", "АПЛ", "Челси"
            )
            self.assertTrue(repository.rename_section("Футбол", "Спорт"))
            item = next(value for value in repository.items() if value.catalog_id == catalog_id)
            self.assertEqual(item.media_type, "Спорт")
            self.assertEqual(repository.sections()[0]["name"], "Спорт")


if __name__ == "__main__":
    unittest.main()
