import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from app.services.catalog_update_service import CatalogChange
from app.ui.dialogs.changelog_dialog import ChangelogDialog, catalog_changelog_html


class ChangelogDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_all_micro_patches_are_rendered_newest_first(self) -> None:
        changes = [
            CatalogChange("AW0.062", {"Игры": 3}),
            CatalogChange("AW0.0991", {"Игры": 0}, updated=40),
        ]
        with patch(
            "app.ui.dialogs.changelog_dialog.CatalogUpdateService.history",
            return_value=changes,
        ):
            html = catalog_changelog_html()
        self.assertIn("AW0.062", html)
        self.assertIn("AW0.0991", html)
        self.assertLess(html.index("AW0.0991"), html.index("AW0.062"))

    def test_major_and_patch_columns_scroll_independently(self) -> None:
        dialog = ChangelogDialog()
        dialog.show()
        self.app.processEvents()
        scroll_areas = dialog.findChildren(QScrollArea)
        self.assertEqual(len(scroll_areas), 2)
        self.assertTrue(all(area.horizontalScrollBar().maximum() == 0 for area in scroll_areas))
        text = " ".join(label.text() for label in dialog.findChildren(QLabel))
        self.assertIn("КРУПНЫЕ ИЗМЕНЕНИЯ AW0.10", text)
        self.assertIn("50, 100, 200 и 500", text)
        self.assertIn("AW0.08", text)
        self.assertIn("AW0.01", text)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
