from pathlib import Path
import sqlite3
import unittest

from app.data.catalog_repository import CATALOG_DB


class CurrentCatalogCoverTests(unittest.TestCase):
    EXPECTED = {
        "g-shooter-aw0092-003": "assets/covers/catalog/apex_legends.jpg",
        "g-shooter-fps-007": "assets/covers/catalog/bioshock.jpg",
        "g-shooter-aw0092-013": "assets/covers/catalog/bioshock_infinite.jpg",
        "g-shooter-tps-003": "assets/covers/catalog/control.jpg",
        "g-shooter-aw0092-001": "assets/covers/catalog/counter_strike_2.jpg",
    }

    def test_aw0221_keeps_five_portable_cover_paths(self) -> None:
        with sqlite3.connect(CATALOG_DB) as connection:
            rows = dict(
                connection.execute(
                    f"SELECT catalog_id, cover_path FROM catalog_items "
                    f"WHERE catalog_id IN ({','.join('?' for _ in self.EXPECTED)})",
                    tuple(self.EXPECTED),
                )
            )
            version = connection.execute(
                "SELECT value FROM metadata WHERE key='catalog_version'"
            ).fetchone()[0]
        self.assertEqual(version, "AW0.301")
        self.assertEqual(rows, self.EXPECTED)
        for relative_path in rows.values():
            path = Path(__file__).resolve().parents[1] / relative_path
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 20_000)


if __name__ == "__main__":
    unittest.main()
