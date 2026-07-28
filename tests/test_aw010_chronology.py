import json
import sqlite3
import unittest
from pathlib import Path


class Aw010ChronologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect(Path(__file__).parents[1] / "data" / "catalog.db")
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_related_cards_share_ordered_chronology(self):
        rows = self.connection.execute(
            "SELECT catalog_id,franchise_name,chronology_json FROM catalog_items "
            "WHERE catalog_id LIKE 'g-%' AND franchise_name<>''"
        ).fetchall()
        self.assertEqual(77, len(rows))
        for row in rows:
            chronology = json.loads(row["chronology_json"])
            self.assertGreaterEqual(len(chronology), 2)
            self.assertEqual(
                list(range(1, len(chronology) + 1)),
                [entry["position"] for entry in chronology],
            )
            self.assertIn(row["catalog_id"], {entry["catalog_id"] for entry in chronology})

    def test_chronology_supports_external_and_unreleased_games(self):
        raw = self.connection.execute(
            "SELECT chronology_json FROM catalog_items WHERE title='Doom Eternal'"
        ).fetchone()[0]
        entries = json.loads(raw)
        self.assertTrue(any(not entry["catalog_id"] for entry in entries))
        self.assertIn("Doom: The Dark Ages", {entry["title"] for entry in entries})

        witcher = json.loads(self.connection.execute(
            "SELECT chronology_json FROM catalog_items WHERE title='The Witcher 3'"
        ).fetchone()[0])
        future = next(entry for entry in witcher if entry["title"] == "The Witcher IV")
        self.assertEqual("", future["catalog_id"])
        self.assertEqual("анонсирована", future["status"])

    def test_obvious_catalog_series_are_linked(self):
        expected = {
            "Medal of Honor",
            "StarCraft II",
            "Warcraft III",
            "Tom Clancy's Rainbow Six Siege",
        }
        rows = self.connection.execute(
            "SELECT title,franchise_name FROM catalog_items WHERE title IN (?,?,?,?)",
            tuple(expected),
        ).fetchall()
        self.assertEqual(expected, {row["title"] for row in rows})
        self.assertTrue(all(row["franchise_name"] for row in rows))


if __name__ == "__main__":
    unittest.main()
