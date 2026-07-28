import sqlite3
import unittest

from app.data.catalog_repository import CATALOG_DB


class CatalogDuplicateTests(unittest.TestCase):
    def test_active_catalog_has_no_duplicate_titles_within_media_type(self) -> None:
        connection = sqlite3.connect(CATALOG_DB)
        try:
            duplicates = connection.execute(
                """
                SELECT lower(trim(title)), media_type, COUNT(*)
                FROM catalog_items
                WHERE is_active=1
                GROUP BY lower(trim(title)), media_type
                HAVING COUNT(*) > 1
                """
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(duplicates, [])

    def test_merged_7zip_card_keeps_metadata_and_scores(self) -> None:
        connection = sqlite3.connect(CATALOG_DB)
        try:
            row = connection.execute(
                """
                SELECT catalog_id, general_score, critic_scores_json,
                       interface_languages_json, system_requirements_json
                FROM catalog_items
                WHERE lower(title)=lower('7-Zip')
                """
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "a-system-pc-7zip-001")
        self.assertAlmostEqual(row[1], 9.2)
        self.assertIn("TechRadar", row[2])
        self.assertNotEqual(row[3], "[]")
        self.assertNotEqual(row[4], "{}")


if __name__ == "__main__":
    unittest.main()
