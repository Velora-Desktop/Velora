from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from app.application import GamesRowQueryService, QueryStateKind
from app.core.paths import AppPaths
from app.core.runtime import set_startup_storage
from app.storage.startup import prepare_aw02_storage
from app.ui.catalog.catalog_view import CatalogView
from app.ui.catalog.single_row_integration import (
    TARGET_GAME_ID, TARGET_LEGACY_GAME_ID, SingleGameRowPresenter,
    SingleGameRowViewModel, build_single_row_presenter,
)


class SingleGamesRowUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.paths = AppPaths.source_run(root=Path(self.temp.name))
        self.storage = prepare_aw02_storage(self.paths)
        set_startup_storage(self.storage)
        facade = GamesRowQueryService(
            self.storage.catalog_db, self.storage.user_db
        )
        self.presenter = SingleGameRowPresenter(SingleGameRowViewModel(facade))
        self.view = CatalogView()
        self.view.single_row_presenter = self.presenter
        self.row = next(
            row for row in self.view.rows
            if row.game.catalog_id == TARGET_LEGACY_GAME_ID
        )

    def tearDown(self):
        self.view.deleteLater()
        self.temp.cleanup()

    def test_default_presenter_is_enabled_without_environment_flags(self):
        self.assertIsNotNone(build_single_row_presenter())

    def test_doom_renders_from_schema_one_without_diagnostic_text(self):
        state = self.presenter.bind(self.row)
        self.assertEqual(state.kind, QueryStateKind.RESULT)
        self.assertEqual(self.row.title_button.text(), "Doom Eternal")
        self.assertNotIn("В библиотеке", self.row.title_button.text())
        self.assertTrue(self.row.more_button.menu().actions())
        self.assertNotIn("AW0.2 READ", self.row.title_button.text())
        self.assertEqual(state.selection.item_id, TARGET_GAME_ID)

    def test_missing_rating_and_playthrough_are_safe(self):
        state = self.presenter.bind(self.row)
        self.assertEqual(state.personal_rating, "—")
        self.assertEqual(self.row.status_button.text(), "НЕ НАЧИНАЛ")

    def test_refresh_only_updates_target_and_preserves_identity(self):
        other = next(row for row in self.view.rows if row is not self.row)
        order = [id(row) for row in self.view.rows]
        other_title = other.title_button.text()
        self.presenter.bind(self.row)
        identity = self.row.aw02_selection_identity
        self.view.refresh_integrated_row(TARGET_LEGACY_GAME_ID)
        self.assertEqual(self.row.aw02_selection_identity, identity)
        self.assertEqual(other.title_button.text(), other_title)
        self.assertEqual([id(row) for row in self.view.rows], order)

    def test_only_doom_is_attached(self):
        other = next(row for row in self.view.rows if row is not self.row)
        self.presenter.bind(self.row)
        self.assertTrue(hasattr(self.row, "aw02_selection_identity"))
        self.assertFalse(hasattr(other, "aw02_selection_identity"))

    def test_refresh_keeps_clickable_cells_on_selected_row_surface(self):
        self.row.set_selected(True)
        self.presenter.refresh(self.row)
        self.assertIn("background:transparent", self.row.title_button.styleSheet())
        self.assertIn(
            "background:transparent", self.row.personal_score_label.styleSheet()
        )
        self.assertIn("background:#160B24", self.row.styleSheet())

    def test_ui_integration_has_no_sql_or_repository_import(self):
        path = Path(__file__).parents[1] / "app/ui/catalog/single_row_integration.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        self.assertNotIn("sqlite3", imports)
        self.assertFalse(any("repositories" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
