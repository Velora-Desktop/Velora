import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from app.ui.catalog.catalog_view import CatalogView
from app.ui.main_window import MainWindow
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.settings_dialog import LANGUAGES, SettingsDialog
from app.ui.quick_view.quick_view import QuickView
from app.ui.navigation.top_bar import TopBar
from app.ui.profile.personal_library_page import PersonalLibraryPage
from app.ui.widgets.platform_icons import PlatformIconRow
from app.data.catalog_repository import load_catalog_items
from app.data.user_repository import UserRepository


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

    def test_catalog_page_size_starts_at_fifty_and_uses_large_steps(self) -> None:
        view = CatalogView()
        self.assertEqual(view.page_size, 50)
        self.assertEqual(
            [view.page_size_combo.itemText(index) for index in range(view.page_size_combo.count())],
            [
                "50 на странице",
                "100 на странице",
                "200 на странице",
                "500 на странице",
            ],
        )
        for index, expected in enumerate((50, 100, 200, 500)):
            view.page_size_combo.setCurrentIndex(index)
            self.app.processEvents()
            self.assertEqual(view.page_size, expected)
        view.close()

    def test_catalog_click_opens_quick_view_then_detail_for_every_media_type(self) -> None:
        view = CatalogView()
        selected = []
        view.game_selected.connect(selected.append)
        quick = QuickView()
        opened = []
        quick.detail_requested.connect(opened.append)
        for media_type in ("Игры", "Фильмы", "Сериалы", "Программы"):
            view.set_media_type(media_type)
            self.app.processEvents()
            self.assertTrue(view.rows, media_type)
            row = view.rows[0]
            row.title_button.click()
            self.app.processEvents()
            self.assertIs(selected[-1], row.game)
            quick.set_game(row.game)
            QTest.mouseClick(quick.summary, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            self.assertIs(opened[-1], row.game)
        view.close()
        quick.close()

    def test_reselecting_current_section_does_not_destroy_rows(self) -> None:
        view = CatalogView()
        view.set_media_type("Сериалы")
        first_row = view.rows[0]
        view.set_media_type("Сериалы", view.current_category)
        self.app.processEvents()
        self.assertIs(view.rows[0], first_row)
        view.close()

    def test_repeated_detail_transitions_across_all_sections_are_stable(self) -> None:
        with patch.object(MainWindow, "_run_first_launch_if_needed", return_value=None):
            window = MainWindow()
        window.show()
        self.app.processEvents()
        samples = []
        for media_type in ("Игры", "Фильмы", "Сериалы", "Программы"):
            samples.extend(
                item for item in window.catalog.items if item.media_type == media_type
            )
        for game in samples[::max(1, len(samples) // 40)]:
            window._on_detail_requested(game)
            self.app.processEvents()
            self.assertIs(window.game_detail.game, game)
            self.assertTrue(window.game_detail.isVisible())
        window.close()

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

    def test_each_catalog_group_keeps_an_independent_sort(self) -> None:
        view = CatalogView()
        groups = list(view.group_rows)
        self.assertGreaterEqual(len(groups), 2)
        first, second = groups[:2]

        view._sort_by_column(first, "year")
        view._sort_by_column(second, "age")
        second_spec = view.group_sort_specs[view._group_sort_key(second)]
        second_order = [row.game.catalog_id for row in view.group_rows[second]]

        view._sort_by_column(first, "year")
        self.assertEqual(
            view.group_sort_specs[view._group_sort_key(first)], ("year", False)
        )
        self.assertEqual(view.group_sort_specs[view._group_sort_key(second)], second_spec)
        self.assertEqual(
            [row.game.catalog_id for row in view.group_rows[second]], second_order
        )
        if view.control_combos[3].count() > 1:
            view.control_combos[3].setCurrentIndex(1)
            self.app.processEvents()
            self.assertEqual(view.group_sort_specs[view._group_sort_key(second)], second_spec)
        view.close()

    def test_top_bar_scrolls_official_and_custom_sections_as_one_strip(self) -> None:
        bar = TopBar()
        bar.resize(1200, 70)
        bar.set_custom_sections(["Футбол", "Книги", "Музыка", "Аниме"])
        bar.show()
        QTest.qWait(50)

        buttons = bar.section_buttons + bar.custom_buttons
        self.assertEqual(bar.back_button.size().toTuple(), (40, 40))
        self.assertEqual(bar.forward_button.size().toTuple(), (40, 40))
        self.assertEqual(
            [button.property("sectionName") for button in buttons[:4]],
            ["ИГРЫ", "ФИЛЬМЫ", "СЕРИАЛЫ", "ПРОГРАММЫ"],
        )
        self.assertTrue(all(button.parent() is bar.section_container for button in buttons))
        scroll = bar.section_scroll.horizontalScrollBar()
        self.assertGreater(scroll.maximum(), 0)
        self.assertFalse(bar.section_back.isVisible())
        self.assertTrue(bar.section_forward.isVisible())

        scroll.setValue(min(150, scroll.maximum()))
        bar._update_section_arrows()
        self.assertTrue(bar.section_back.isVisible())
        bar.set_active_space("ИГРЫ")
        QTest.qWait(10)
        self.assertEqual(scroll.value(), 0)
        bar._section_animation.setDuration(200)
        bar.section_forward.click()
        bar.prepare_section_removal()
        bar.set_custom_sections(["Футбол"])
        QTest.qWait(10)
        self.assertEqual(scroll.value(), 0)
        bar.close()

    def test_hidden_personal_library_can_be_refreshed_repeatedly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = UserRepository(Path(directory) / "user.db")
            page = PersonalLibraryPage(repository)
            items = load_catalog_items()[:12]
            for _ in range(12):
                page.refresh(items)
                self.app.processEvents()
            self.assertGreater(page.smart_lists.count(), 0)
            page.close()


if __name__ == "__main__":
    unittest.main()
