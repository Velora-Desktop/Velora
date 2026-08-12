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
        self.assertEqual(78, len(rows))
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

    def test_chronology_catalog_ids_are_unique_and_unambiguous(self):
        rows = self.connection.execute(
            "SELECT catalog_id,title,chronology_json FROM catalog_items "
            "WHERE chronology_json<>'[]'"
        ).fetchall()
        for row in rows:
            entries = json.loads(row["chronology_json"])
            linked_ids = [
                entry["catalog_id"] for entry in entries if entry["catalog_id"]
            ]
            self.assertEqual(
                len(linked_ids), len(set(linked_ids)),
                f"{row['catalog_id']} ({row['title']}) reuses a catalog ID",
            )

    def test_same_title_editions_are_distinct_catalog_objects(self):
        rows = self.connection.execute(
            "SELECT catalog_id,release_year,cover_path FROM catalog_items "
            "WHERE title='God of War' ORDER BY release_year"
        ).fetchall()
        self.assertEqual([2005, 2018], [row["release_year"] for row in rows])
        self.assertEqual(2, len({row["catalog_id"] for row in rows}))
        self.assertEqual(2, len({row["cover_path"] for row in rows}))

    def test_same_title_chronology_nodes_use_distinct_year_specific_covers(self):
        rows = self.connection.execute(
            "SELECT franchise_name,chronology_json FROM catalog_items "
            "WHERE chronology_json<>'[]'"
        ).fetchall()
        checked: set[str] = set()
        for row in rows:
            if row["franchise_name"] in checked:
                continue
            checked.add(row["franchise_name"])
            entries = json.loads(row["chronology_json"])
            by_title: dict[str, list[dict]] = {}
            for entry in entries:
                by_title.setdefault(entry["title"].casefold(), []).append(entry)
            for title, editions in by_title.items():
                if len(editions) < 2:
                    continue
                years = {entry.get("release_year") for entry in editions}
                paths = {entry.get("cover_path") for entry in editions}
                self.assertEqual(
                    len(editions), len(years),
                    f"{row['franchise_name']} / {title} repeats an edition year",
                )
                self.assertNotIn("", paths)
                self.assertEqual(
                    len(editions), len(paths),
                    f"{row['franchise_name']} / {title} reuses one cover",
                )


if __name__ == "__main__":
    unittest.main()
