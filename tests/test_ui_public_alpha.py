import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.ui.catalog.catalog_view import CatalogView
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.settings_dialog import LANGUAGES, SettingsDialog
from app.ui.quick_view.quick_view import QuickView
from app.ui.widgets.platform_icons import PlatformIconRow


class PublicAlphaUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_catalog_controls_reflow_at_small_width(self) -> None:
        view = CatalogView(); view.resize(1000, 700); view.show(); self.app.processEvents()
        self.assertTrue(view._controls_compact)
        self.assertTrue(view.settings_button.isVisible())
        self.assertTrue(all(combo.width() >= 170 for combo in view.control_combos))
        view.resize(1600, 900); self.app.processEvents()
        self.assertFalse(view._controls_compact)
        view.close()

    def test_public_alpha_dialog_content_and_quick_view_bounds(self) -> None:
        settings = SettingsDialog(True, ())
        language_buttons = [button for button in settings.findChildren(QPushButton) if button.text().startswith(tuple(name for name, _, _ in LANGUAGES))]
        self.assertEqual(len(language_buttons), len(LANGUAGES))
        self.assertEqual(sum(bool(button.property("future")) for button in language_buttons), len(LANGUAGES) - 1)
        about = AboutDialog()
        self.assertIn("Flaticon", " ".join(label.text() for label in about.findChildren(QLabel)))
        quick = QuickView()
        self.assertLessEqual(quick.maximumHeight(), 380)

    def test_catalog_group_headers_share_the_row_column_grid(self) -> None:
        view = CatalogView(); view.resize(970, 620); view.show(); self.app.processEvents()
        for media_type in ("Игры", "Фильмы", "Сериалы", "Программы"):
            view.set_media_type(media_type); self.app.processEvents()
            view.scroll.horizontalScrollBar().setValue(view.scroll.horizontalScrollBar().maximum())
            self.app.processEvents()
            first_group = next(iter(view.group_labels.values()))
            headers = view.header_column_widgets[first_group]
            row = view.rows[0]
            for key in ("general", "personal", "status", "developer", "year", "platform", "mode", "age"):
                header = headers[key]
                value = row.column_widgets[key]
                header_center = header.mapTo(view.content, header.rect().center()).x()
                value_center = value.mapTo(view.content, value.rect().center()).x()
                self.assertLessEqual(abs(header_center - value_center), 2, f"{media_type}:{key}")
        view.close()

    def test_group_toggle_and_semantic_platform_deduplication(self) -> None:
        view = CatalogView(); view.resize(1500, 720); view.show(); self.app.processEvents()
        group_name = next(iter(view.group_rows))
        header = view.group_labels[group_name]
        toggle = header.findChild(QPushButton, "groupToggle")
        self.assertIsNotNone(toggle)
        self.assertEqual(toggle.text(), "\u2212")
        toggle.click(); self.app.processEvents()
        self.assertTrue(all(not row.isVisible() for row in view.group_rows[group_name]))
        self.assertEqual(toggle.text(), "+")
        toggle.click(); self.app.processEvents()
        self.assertTrue(any(row.isVisible() for row in view.group_rows[group_name]))

        platforms = PlatformIconRow("iOS; iPhone; Windows; PC", max_icons=5)
        self.assertEqual(len(platforms.findChildren(QLabel)), 2)
        view.close()


if __name__ == "__main__":
    unittest.main()
