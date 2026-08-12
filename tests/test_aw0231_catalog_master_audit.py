import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.db"


class CatalogMasterAuditTests(unittest.TestCase):
    def test_active_game_identity_is_unique(self):
        with sqlite3.connect(CATALOG) as connection:
            rows = connection.execute(
                "SELECT catalog_id,title,release_year FROM catalog_items "
                "WHERE catalog_id LIKE 'g-%' AND is_active=1"
            ).fetchall()
        self.assertEqual(101, len(rows))
        self.assertEqual(len(rows), len({row[0] for row in rows}))
        collisions = {}
        for game_id, title, year in rows:
            collisions.setdefault((title.casefold(), year), []).append(game_id)
        self.assertFalse({key: ids for key, ids in collisions.items() if len(ids) > 1})

    def test_all_game_covers_are_local_and_readable(self):
        from PySide6.QtGui import QImage

        with sqlite3.connect(CATALOG) as connection:
            paths = connection.execute(
                "SELECT catalog_id,cover_path FROM catalog_items "
                "WHERE catalog_id LIKE 'g-%' AND is_active=1"
            ).fetchall()
        for game_id, relative_path in paths:
            path = ROOT / relative_path
            self.assertTrue(path.is_file(), game_id)
            self.assertFalse(QImage(str(path)).isNull(), game_id)

    def test_manifests_cover_every_active_game(self):
        audit = json.loads((ROOT / "data" / "aw0231_catalog_master_audit.json").read_text(encoding="utf-8"))
        manual = json.loads((ROOT / "data" / "aw0231_catalog_manual_review.json").read_text(encoding="utf-8"))
        self.assertEqual(101, len(audit["games"]))
        valid = {"verified", "corrected", "missing", "manual_review", "not_applicable"}
        self.assertTrue(all(set(game["fields"].values()) <= valid for game in audit["games"]))
        self.assertTrue(all(item["confidence"] == "LOW" for item in manual["items"]))

    def test_catalog_integrity(self):
        with sqlite3.connect(CATALOG) as connection:
            self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())


if __name__ == "__main__":
    unittest.main()
