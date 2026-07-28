import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.data.user_repository import UserRepository


class Aw010CatalogTagTests(unittest.TestCase):
    def test_every_game_has_at_least_three_official_tags(self):
        connection = sqlite3.connect(Path(__file__).parents[1] / "data" / "catalog.db")
        try:
            rows = connection.execute(
                "SELECT catalog_id,title,catalog_tags_json FROM catalog_items "
                "WHERE catalog_id LIKE 'g-%' AND is_active=1"
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(100, len(rows))
        for catalog_id, title, raw_tags in rows:
            tags = json.loads(raw_tags)
            self.assertGreaterEqual(len(tags), 3, f"{catalog_id}: {title}")
            self.assertEqual(len(tags), len({value.casefold() for value in tags}))
        doom = next(tags for _id, title, tags in rows if title == "Doom Eternal")
        self.assertIn("космос", json.loads(doom))

    def test_personal_tags_can_be_renamed_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = UserRepository(Path(directory) / "user.db")
            tag_id = repository.add_tag("Для ролика")
            repository.assign_tag("g-test-001", tag_id)
            repository.rename_tag(tag_id, "Материал для ролика")
            self.assertEqual("Материал для ролика", repository.tags()[0][1])
            self.assertEqual([tag_id], repository.tag_ids_for("g-test-001"))
            repository.delete_tag(tag_id)
            self.assertEqual([], repository.tags())
            self.assertEqual([], repository.tag_ids_for("g-test-001"))


if __name__ == "__main__":
    unittest.main()
