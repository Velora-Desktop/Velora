import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
DB = ROOT / "data" / "catalog.db"
MANIFEST = ROOT / "assets" / "covers" / "chronology" / "aw0231_chronology_cover_sources.json"


class AW0231ChronologyCoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(DB)
        cls.db.row_factory = sqlite3.Row
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _groups(self):
        result = {}
        for row in self.db.execute(
            "SELECT franchise_name,chronology_json FROM catalog_items "
            "WHERE franchise_name<>''"
        ):
            result.setdefault(row["franchise_name"], json.loads(row["chronology_json"]))
        return result

    def test_every_chronology_node_is_local_or_explicit_manual_review(self):
        manual = {
            (item["franchise"], item["title"])
            for item in self.manifest["manual_review"]
        }
        for franchise, entries in self._groups().items():
            for entry in entries:
                path = str(entry.get("cover_path") or "")
                if path:
                    self.assertFalse(path.startswith(("http://", "https://")))
                    self.assertTrue((ROOT / path).is_file(), (franchise, entry["title"], path))
                else:
                    self.assertIn((franchise, entry["title"]), manual)

    def test_dishonored_chronology_has_three_valid_covers(self):
        entries = self._groups()["Dishonored"]
        self.assertEqual([item["title"] for item in entries], [
            "Dishonored", "Dishonored 2", "Dishonored: Death of the Outsider",
        ])
        self.assertTrue(all((ROOT / item["cover_path"]).is_file() for item in entries))

    def test_doom_reboots_have_year_specific_covers(self):
        editions = [
            item for item in self._groups()["Doom"]
            if item["title"] == "Doom"
        ]
        self.assertEqual([1993, 2016], [item["release_year"] for item in editions])
        self.assertEqual(2, len({item["cover_path"] for item in editions}))
        self.assertTrue(all((ROOT / item["cover_path"]).is_file() for item in editions))

    def test_catalog_integrity(self):
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
