from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.data import catalog_repository
from app.models.game import GameData
from app.ui.game_detail.game_detail_page import GameDetailPage


class EngineAndAntiCheatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _legacy_database(self, path: Path, *, engine_columns: bool) -> None:
        with closing(sqlite3.connect(path)) as connection:
            suffix = ", engine TEXT, anti_cheat TEXT" if engine_columns else ""
            connection.execute(
                "CREATE TABLE catalog_items("
                "catalog_id TEXT PRIMARY KEY,media_type TEXT,title TEXT,category TEXT,"
                "subgroup TEXT,age_rating INTEGER,is_active INTEGER,updated_at TEXT"
                f"{suffix})"
            )
            columns = "catalog_id,media_type,title,category,subgroup,age_rating,is_active,updated_at"
            values = ["g-test", "Игры", "Test", "Шутеры", "FPS", 16, 1, "now"]
            if engine_columns:
                columns += ",engine,anti_cheat"
                values += ["Source 2", "VAC"]
            connection.execute(
                f"INSERT INTO catalog_items({columns}) VALUES({','.join('?' for _ in values)})",
                values,
            )
            connection.commit()

    def test_old_catalog_without_technical_fields_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.db"
            self._legacy_database(path, engine_columns=False)
            with patch.object(catalog_repository, "CATALOG_DB", path):
                item = catalog_repository.load_catalog_items()[0]
            self.assertEqual((item.engine, item.anti_cheat), ("", ""))

    def test_new_technical_fields_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.db"
            self._legacy_database(path, engine_columns=True)
            with patch.object(catalog_repository, "CATALOG_DB", path):
                item = catalog_repository.load_catalog_items()[0]
            self.assertEqual((item.engine, item.anti_cheat), ("Source 2", "VAC"))

    def test_game_detail_replaces_distribution_with_engine_block(self) -> None:
        game = GameData(
            "Test", "8.0", "—", "НЕ НАЧИНАЛ", "Dev", "2024", "PC", "1P",
            catalog_id="g-test", media_type="Игры", distribution_model="Платное",
            engine="Source 2", anti_cheat="VAC",
        )
        page = GameDetailPage()
        page._fill_official_details(game)
        texts = [label.text() for label in page.findChildren(QLabel)]
        self.assertIn("ДВИЖОК", texts)
        self.assertIn("Source 2", texts)
        self.assertIn("АНТИЧИТ", texts)
        self.assertIn("VAC", texts)
        self.assertNotIn("РАСПРОСТРАНЕНИЕ", texts)
        page.close()

    def test_empty_technical_values_do_not_create_empty_block(self) -> None:
        game = GameData(
            "Test", "8.0", "—", "НЕ НАЧИНАЛ", "Dev", "2024", "PC", "1P",
            catalog_id="g-test", media_type="Игры",
        )
        page = GameDetailPage()
        page._fill_official_details(game)
        self.assertNotIn("ДВИЖОК", [label.text() for label in page.findChildren(QLabel)])
        page.close()


if __name__ == "__main__":
    unittest.main()
