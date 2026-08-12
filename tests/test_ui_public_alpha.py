import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtTest import QTest
from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QPixmap

from app.ui.catalog.catalog_view import CatalogView
from app.ui.main_window import MainWindow
from app.ui.dialogs.about_dialog import AboutDialog, VELORA_GITHUB_URL
from app.ui.dialogs.settings_dialog import LANGUAGES, SettingsDialog
from app.ui.quick_view.quick_view import QuickView
from app.ui.navigation.top_bar import TopBar
from app.ui.navigation.v_menu import VMenu
from app.ui.velora_ui.components import AnimatedSearchLineEdit, HoverAnimatedIcon
from app.ui.profile.personal_library_page import PersonalLibraryPage
from app.ui.profile.profile_page import ProfilePage
from app.ui.profile.profile_dialog import ProfileDialog
from app.ui.profile.profile_widgets import AvatarLabel, AvatarPicker
from app.ui.widgets.platform_icons import PlatformIconRow, platform_tokens
from app.ui.game_detail.game_detail_page import GameDetailPage
from app.application.game_row_contracts import GameRowAction
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

    def test_default_profile_avatar_animates_but_custom_avatar_keeps_priority(self) -> None:
        avatar = AvatarLabel(124)
        animated = avatar.findChild(HoverAnimatedIcon, "animatedDefaultAvatar")
        self.assertIsNotNone(animated)
        avatar.show()
        self.app.processEvents()
        self.assertTrue(animated.isVisible())
        self.assertTrue(animated._sequence_timer.isActive())
        with tempfile.TemporaryDirectory() as directory:
            custom_path = Path(directory) / "avatar.png"
            animated._sequence_frames[0].save(str(custom_path))
            avatar.set_avatar(str(custom_path))
            self.assertFalse(animated.isVisible())
            self.assertFalse(avatar.pixmap().isNull())
        avatar.set_avatar("")
        self.assertTrue(animated.isVisible())
        avatar.close()
        avatar.deleteLater()
        self.app.processEvents()

    def test_profile_editor_uses_large_avatar_choices_without_personal_statistics(self) -> None:
        class RepositoryStub:
            def load_profile(self):
                from app.data.user_repository import LocalProfile
                return LocalProfile("Velora", "Описание", "")

            def save_profile(self, profile):
                self.saved = profile

        dialog = ProfileDialog(RepositoryStub(), ())
        picker = dialog.findChild(AvatarPicker, "profileAvatarPicker")
        self.assertIsNotNone(picker)
        self.assertEqual(picker.custom_button.size().toTuple(), (176, 176))
        self.assertEqual(picker.default_button.size().toTuple(), (176, 176))
        self.assertGreaterEqual(picker.minimumHeight(), 184)
        self.assertTrue(picker.default_button.property("selected"))
        self.assertIn(
            'QPushButton#defaultAvatarChoice[selected="true"]',
            picker.styleSheet(),
        )
        button_texts = {button.text() for button in dialog.findChildren(QPushButton)}
        self.assertNotIn("ВЫБРАТЬ ИЗОБРАЖЕНИЕ", button_texts)
        self.assertNotIn("УБРАТЬ АВАТАР", button_texts)
        label_text = "\n".join(label.text() for label in dialog.findChildren(QLabel))
        self.assertNotIn("ЛИЧНАЯ СТАТИСТИКА", label_text)
        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_avatar_picker_replaces_plus_with_preview_and_keeps_selected_border(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            avatar_path = Path(directory) / "avatar.png"
            pixmap = QPixmap(80, 120)
            pixmap.fill(Qt.GlobalColor.white)
            self.assertTrue(pixmap.save(str(avatar_path)))
            picker = AvatarPicker()
            picker.set_custom_avatar(str(avatar_path))
            self.assertEqual(picker.custom_button.text(), "")
            self.assertFalse(picker.custom_button.icon().isNull())
            self.assertTrue(picker.custom_button.property("selected"))
            self.assertFalse(picker.default_button.property("selected"))
            picker.default_button.click()
            self.assertTrue(picker.default_button.property("selected"))
            self.assertFalse(picker.custom_button.property("selected"))
            self.assertFalse(picker.custom_button.icon().isNull())
            picker.custom_button.click()
            self.assertTrue(picker.custom_button.property("selected"))
            self.assertFalse(picker.default_button.property("selected"))
            picker.close()
            picker.deleteLater()
            self.app.processEvents()

    def test_settings_animation_is_used_by_catalog_and_application_menu(self) -> None:
        view = CatalogView()
        self.assertIsNotNone(
            view.settings_button.findChild(
                HoverAnimatedIcon, "catalogAnimatedSettingsIcon"
            )
        )
        menu = VMenu()
        row = menu.findChild(QPushButton, "animatedSettingsMenuRow")
        self.assertIsNotNone(row)
        self.assertEqual(row.height(), 58)
        self.assertEqual(row.layout().contentsMargins().left(), 0)
        label = row.findChild(QLabel, "animatedSettingsMenuRowLabel")
        self.assertIn("#FFFFFF", label.styleSheet())
        QApplication.sendEvent(row, QEvent(QEvent.Type.Enter))
        self.assertTrue(row.property("hovered"))
        self.assertIn("#C77DFF", label.styleSheet())
        QApplication.sendEvent(row, QEvent(QEvent.Type.Leave))
        self.assertFalse(row.property("hovered"))
        self.assertIn("#FFFFFF", label.styleSheet())
        self.assertIsNotNone(
            row.findChild(HoverAnimatedIcon, "menuAnimatedSettingsIcon")
        )
        about_icon = menu.findChild(
            HoverAnimatedIcon, "aboutMenuRowAnimatedIcon"
        )
        self.assertIsNotNone(about_icon)
        self.assertFalse(about_icon._autoplay)
        self.assertEqual(len(about_icon._sequence_frames), 28)
        exit_icon = menu.findChild(
            HoverAnimatedIcon, "exitMenuRowAnimatedIcon"
        )
        self.assertIsNotNone(exit_icon)
        self.assertFalse(exit_icon._autoplay)
        self.assertEqual(len(exit_icon._sequence_frames), 28)
        about_row = menu.findChild(QPushButton, "aboutMenuRow")
        exit_row = menu.findChild(QPushButton, "exitMenuRow")
        QApplication.sendEvent(about_row, QEvent(QEvent.Type.Enter))
        QApplication.sendEvent(exit_row, QEvent(QEvent.Type.Enter))
        self.assertTrue(about_icon._sequence_timer.isActive())
        self.assertTrue(exit_icon._sequence_timer.isActive())
        QApplication.sendEvent(about_row, QEvent(QEvent.Type.Leave))
        QApplication.sendEvent(exit_row, QEvent(QEvent.Type.Leave))
        self.assertFalse(about_icon._sequence_timer.isActive())
        self.assertFalse(exit_icon._sequence_timer.isActive())
        aligned_rows = [
            menu.findChild(QPushButton, name)
            for name in (
                "animatedSettingsMenuRow", "aboutMenuRow", "changelogMenuRow",
                "supportMenuRow", "exitMenuRow",
            )
        ]
        self.assertTrue(all(item is not None for item in aligned_rows))
        self.assertTrue(all(item.layout().contentsMargins().left() == 0 for item in aligned_rows))
        self.assertTrue(all(item.layout().itemAt(0).widget().width() == 20 for item in aligned_rows))
        view.close()
        menu.close()

    def test_settings_language_heading_uses_constant_animated_flag(self) -> None:
        dialog = SettingsDialog(False, [])
        icon = dialog.findChild(
            HoverAnimatedIcon, "animatedInterfaceLanguageIcon"
        )
        self.assertIsNotNone(icon)
        self.assertTrue(icon._autoplay)
        self.assertEqual(len(icon._sequence_frames), 28)
        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_catalog_settings_can_hide_and_restore_a_group(self) -> None:
        settings = QSettings("Velora", "Velora")
        previous = settings.value("catalog/hidden_groups", None)
        settings.setValue("catalog/hidden_groups", "{}")
        view = CatalogView()
        try:
            group_name = next(iter(view.group_rows))
            rows = view.group_rows[group_name]
            self.assertTrue(any(row.isVisibleTo(view.content) for row in rows))
            view._set_group_visibility(group_name, False)
            self.assertTrue(all(not row.isVisible() for row in rows))
            self.assertFalse(view.group_labels[group_name].isVisible())
            view._set_group_visibility(group_name, True)
            self.assertTrue(any(row.isVisibleTo(view.content) for row in rows))
        finally:
            view.close()
            if previous is None:
                settings.remove("catalog/hidden_groups")
            else:
                settings.setValue("catalog/hidden_groups", previous)

    def test_catalog_column_headers_have_purple_text_hover_without_fill(self) -> None:
        view = CatalogView()
        buttons = view.findChildren(QPushButton, "catalogColumnHeaderButton")
        self.assertTrue(buttons)
        style = view.styleSheet()
        self.assertIn(
            "QPushButton#catalogColumnHeaderButton:hover", style
        )
        self.assertIn("color:#CFA1FF", style)
        self.assertIn("background:transparent", style)
        view.close()

    def test_quick_view_time_action_has_explicit_velora_hover(self) -> None:
        quick = QuickView()
        style = quick.time_button.styleSheet()
        self.assertIn("QPushButton#timeAction:hover", style)
        self.assertIn("color:#8B2CF5", style)
        self.assertIn("border-color:#8B2CF5", style)
        quick.close()

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

    def test_game_row_quick_access_does_not_duplicate_journey_actions(self) -> None:
        view = CatalogView()
        row = view.rows[0]
        row.set_aw02_actions(tuple(GameRowAction))
        texts = [action.text() for action in row.more_button.menu().actions()]
        self.assertEqual(
            texts,
            ["Добавить/убрать из избранного", "Скрыть у меня"],
        )
        view.close()

    def test_xbox_series_xs_is_one_platform_not_a_stray_s(self) -> None:
        tokens = platform_tokens(
            "PC; PlayStation 5; Xbox Series X/S; Nintendo Switch"
        )
        self.assertIn("Xbox Series X/S", tokens)
        self.assertIn("Nintendo Switch", tokens)
        self.assertNotIn("S", tokens)

        row = PlatformIconRow(
            "PC; PlayStation 5; Xbox Series X/S; Nintendo Switch",
            max_icons=3,
        )
        overflow = next(
            label for label in row.findChildren(QLabel)
            if label.text().startswith("+")
        )
        self.assertNotIn(", S", overflow.toolTip())

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
            opened.clear()
            QTest.mouseClick(quick.summary, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            self.assertFalse(opened)
            quick.title_button.click()
            self.app.processEvents()
            self.assertIs(opened[-1], row.game)
        view.close()
        quick.close()

    def test_only_quick_view_title_opens_full_detail(self) -> None:
        quick = QuickView()
        game = load_catalog_items()[0]
        opened = []
        quick.detail_requested.connect(opened.append)
        quick.set_game(game)
        passive_targets = [
            quick.summary,
            quick.general_score,
            quick.personal_score,
            quick.playtime,
        ]
        for target in passive_targets:
            QTest.mouseClick(target, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        self.assertEqual(opened, [])
        self.assertFalse(
            any(
                bool(widget.property("quickDetailTarget"))
                for widget in quick.findChildren(QLabel)
            )
        )
        quick.title_button.click()
        self.app.processEvents()
        self.assertEqual(opened, [game])
        quick.close()

    def test_game_about_and_journey_tabs_switch_without_rebuilding(self) -> None:
        game = next(
            item for item in load_catalog_items()
            if item.catalog_id == "g-shooter-fps-002"
        )
        page = GameDetailPage()
        # This test verifies widget identity and tab navigation only.  Storage
        # integration has its own tests and must not open a modal when the
        # isolated UI test profile has no AW0.2 Doom projection.
        with patch.object(page.aw02_panel, "refresh", return_value=None):
            page.set_game(game)
        panel_identity = id(page.aw02_panel)
        journey_identity = id(page.aw02_panel.journey_page)
        for index in range(120):
            page.content_tabs.setCurrentIndex(index % 2)
        self.app.processEvents()
        self.assertEqual(id(page.aw02_panel), panel_identity)
        self.assertEqual(id(page.aw02_panel.journey_page), journey_identity)
        self.assertTrue(page.content_tabs.isTabEnabled(1))
        page.close()

    def test_journey_responsive_profiles_keep_fullhd_and_2k_scrollbar_free(self) -> None:
        """Timeline width must not inflate the outer game-detail scroll area."""
        from app.application.journey_presentation import JourneyPresentationBuilder
        from tests.test_aw021_journey_templates import make_state

        game = next(
            item for item in load_catalog_items()
            if item.catalog_id == "g-shooter-fps-002"
        )
        expected = {
            (1920, 1080): ("fullhd", (170, 255)),
            (2560, 1440): ("expanded", (210, 315)),
        }
        for size, (profile, cover_size) in expected.items():
            page = GameDetailPage()
            page.resize(*size)
            page.show()
            with patch.object(page.aw02_panel, "refresh", return_value=None):
                page.set_game(game)
            page.content_tabs.setCurrentIndex(1)
            page.aw02_panel.journey_page.set_presentation(
                JourneyPresentationBuilder().build(make_state())
            )
            for _ in range(4):
                self.app.processEvents()
                page._apply_responsive_profile()
            self.assertEqual(page.property("journeyResponsiveProfile"), profile)
            self.assertEqual(page.cover.size().toTuple(), cover_size)
            self.assertEqual(page.horizontalScrollBar().maximum(), 0)
            self.assertEqual(page.verticalScrollBar().maximum(), 0)
            self.assertEqual(
                page.aw02_panel.journey_page.timeline_scroll.verticalScrollBar().maximum(),
                0,
            )
            page.close()

    def test_journey_small_profile_preserves_readable_components(self) -> None:
        game = next(
            item for item in load_catalog_items()
            if item.catalog_id == "g-shooter-fps-002"
        )
        page = GameDetailPage()
        page.resize(1366, 768)
        page.show()
        with patch.object(page.aw02_panel, "refresh", return_value=None):
            page.set_game(game)
        page.content_tabs.setCurrentIndex(1)
        self.app.processEvents()
        self.assertEqual(page.property("journeyResponsiveProfile"), "small")
        self.assertEqual(page.cover.size().toTuple(), (140, 210))
        self.assertEqual(page.horizontalScrollBar().maximum(), 0)
        page.close()

    def test_all_game_detail_headers_keep_compact_geometry(self) -> None:
        """Sparse catalog metadata must never stretch the shared hero row."""
        games = [
            item for item in load_catalog_items()
            if item.media_type == "Игры"
        ]
        page = GameDetailPage()
        page.resize(1295, 700)
        page.show()
        with patch.object(page.aw02_panel, "refresh", return_value=None):
            for game in games:
                page.set_game(game)
                self.app.processEvents()
                content = page.widget()
                cover_top = page.cover.mapTo(content, page.cover.rect().topLeft()).y()
                title_top = page.title.mapTo(content, page.title.rect().topLeft()).y()
                tabs_top = page.content_tabs.mapTo(
                    content, page.content_tabs.rect().topLeft()
                ).y()
                self.assertLessEqual(
                    abs(cover_top - title_top), 24,
                    f"Hero alignment drifted for {game.catalog_id}: {game.title}",
                )
                cover_bottom = cover_top + page.cover.height()
                description_top = page.description.mapTo(
                    content, page.description.rect().topLeft()
                ).y()
                hero_bottom = max(
                    cover_bottom, description_top + page.description.height()
                )
                self.assertLessEqual(
                    tabs_top - hero_bottom, 90,
                    f"Unexpected blank hero space for {game.catalog_id}: {game.title}",
                )
        page.close()

    def test_developer_icon_is_animated_in_detail_and_quick_view(self) -> None:
        page = GameDetailPage()
        detail_icon = page.findChild(
            HoverAnimatedIcon, "animatedDeveloperMetadataIcon"
        )
        self.assertIsNotNone(detail_icon)
        self.assertTrue(detail_icon._autoplay)
        quick = QuickView()
        quick_icon = quick.findChild(
            HoverAnimatedIcon, "quickViewAnimatedDeveloperIcon"
        )
        self.assertIsNotNone(quick_icon)
        self.assertTrue(quick_icon._autoplay)
        page.close()
        quick.close()

    def test_studio_icon_is_constant_animation_for_movies_and_series(self) -> None:
        items = load_catalog_items()
        movie = next(item for item in items if item.media_type == "Фильмы")
        game = next(item for item in items if item.media_type == "Игры")
        page = GameDetailPage()
        page.set_game(movie)
        detail_icon = page.findChild(
            HoverAnimatedIcon, "animatedStudioMetadataIcon"
        )
        self.assertIs(page.studio_icon_stack.currentWidget(), detail_icon)
        self.assertTrue(detail_icon._autoplay)
        page.set_game(game)
        self.assertIsNot(page.studio_icon_stack.currentWidget(), detail_icon)

        quick = QuickView()
        quick.set_game(movie)
        quick_icon = quick.findChild(
            HoverAnimatedIcon, "quickViewAnimatedStudioIcon"
        )
        self.assertIs(quick.studio_icon_stack.currentWidget(), quick_icon)
        self.assertTrue(quick_icon._autoplay)
        quick.set_game(game)
        self.assertIsNot(quick.studio_icon_stack.currentWidget(), quick_icon)
        page.close()
        quick.close()

    def test_platform_and_watch_icons_switch_for_media_type_everywhere(self) -> None:
        items = load_catalog_items()
        movie = next(item for item in items if item.media_type == "Фильмы")
        game = next(item for item in items if item.media_type == "Игры")

        page = GameDetailPage()
        page.set_game(game)
        detail_platform = page.findChild(
            HoverAnimatedIcon, "animatedPlatformMetadataIcon"
        )
        detail_ticket = page.findChild(
            HoverAnimatedIcon, "animatedWatchMetadataIcon"
        )
        self.assertIs(page.platform_icon_stack.currentWidget(), detail_platform)
        page.set_game(movie)
        self.assertIs(page.platform_icon_stack.currentWidget(), detail_ticket)
        self.assertTrue(detail_platform._autoplay)
        self.assertTrue(detail_ticket._autoplay)

        quick = QuickView()
        quick.set_game(game)
        quick_platform = quick.findChild(
            HoverAnimatedIcon, "quickViewAnimatedPlatformIcon"
        )
        quick_ticket = quick.findChild(
            HoverAnimatedIcon, "quickViewAnimatedWatchIcon"
        )
        self.assertIs(quick.platform_icon_stack.currentWidget(), quick_platform)
        quick.set_game(movie)
        self.assertIs(quick.platform_icon_stack.currentWidget(), quick_ticket)
        self.assertTrue(quick_platform._autoplay)
        self.assertTrue(quick_ticket._autoplay)
        page.close()
        quick.close()

    def test_journey_tab_is_visible_only_for_games(self) -> None:
        items = load_catalog_items()
        game = next(item for item in items if item.media_type == "Игры")
        movie = next(item for item in items if item.media_type == "Фильмы")
        series = next(item for item in items if item.media_type == "Сериалы")
        software = next(item for item in items if item.media_type == "Программы")
        page = GameDetailPage()

        page.set_game(game)
        self.assertTrue(page.content_tabs.isTabVisible(1))
        self.assertTrue(page.content_tabs.isTabEnabled(1))
        page.content_tabs.setCurrentIndex(1)

        for item in (movie, series, software):
            page.set_game(item)
            self.assertEqual(page.content_tabs.currentIndex(), 0)
            self.assertFalse(page.content_tabs.isTabVisible(1))
            self.assertFalse(page.content_tabs.isTabEnabled(1))

        page.set_game(game)
        self.assertTrue(page.content_tabs.isTabVisible(1))
        self.assertTrue(page.content_tabs.isTabEnabled(1))
        page.close()

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
        project_link = about.findChild(QPushButton, "aboutProjectLink")
        self.assertIsNotNone(project_link)
        self.assertEqual(project_link.text(), "VELORA")
        self.assertTrue(project_link.icon().isNull())
        with patch("app.ui.dialogs.about_dialog.QDesktopServices.openUrl") as open_url:
            project_link.click()
            open_url.assert_called_once()
            self.assertEqual(open_url.call_args.args[0].toString(), VELORA_GITHUB_URL)
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
        title = header.findChild(QPushButton, "groupTitle")
        self.assertIsNotNone(toggle)
        self.assertIsNotNone(title)
        self.assertEqual(toggle.text(), "\u2212")
        toggle.click(); self.app.processEvents()
        self.assertTrue(all(not row.isVisible() for row in view.group_rows[group_name]))
        self.assertEqual(toggle.text(), "+")
        toggle.click(); self.app.processEvents()
        self.assertTrue(any(row.isVisible() for row in view.group_rows[group_name]))
        title.click(); self.app.processEvents()
        self.assertTrue(all(not row.isVisible() for row in view.group_rows[group_name]))
        title.click(); self.app.processEvents()
        self.assertTrue(any(row.isVisible() for row in view.group_rows[group_name]))
        self.assertIn("QPushButton#groupTitle:hover", view.styleSheet())

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

        self.assertEqual(bar.back_button.objectName(), "navigationHistoryButton")
        self.assertEqual(bar.forward_button.objectName(), "navigationHistoryButton")
        self.assertIsNotNone(
            bar.back_button.findChild(
                HoverAnimatedIcon, "animatedNavigationArrowLeft"
            )
        )
        self.assertIsNotNone(
            bar.forward_button.findChild(
                HoverAnimatedIcon, "animatedNavigationArrowRight"
            )
        )
        self.assertTrue(bar.back_button.isEnabled())
        self.assertTrue(bar.forward_button.isEnabled())
        self.assertFalse(bar.back_button.property("navigationAvailable"))
        self.assertFalse(bar.forward_button.property("navigationAvailable"))
        bar.set_history_availability(True, False)
        self.assertTrue(bar.back_button.isEnabled())
        self.assertTrue(bar.forward_button.isEnabled())
        self.assertTrue(bar.back_button.property("navigationAvailable"))
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

    def test_search_controls_keep_click_and_input_behavior(self) -> None:
        bar = TopBar()
        requested = []
        bar.search_requested.connect(lambda: requested.append(True))
        bar.search_button.click()
        self.assertEqual(requested, [True])
        self.assertIsNotNone(
            bar.search_button.findChild(HoverAnimatedIcon, "topBarAnimatedSearchIcon")
        )
        plus_icon = bar.add_button.findChild(
            HoverAnimatedIcon, "topBarAnimatedPlusIcon"
        )
        self.assertIsNotNone(plus_icon)
        self.assertEqual(len(plus_icon._sequence_frames), 28)
        self.assertEqual(bar.add_button.text(), "")
        self.assertEqual(bar.add_button.size(), bar.search_button.size())
        QApplication.sendEvent(bar.add_button, QEvent(QEvent.Type.Enter))
        self.assertTrue(plus_icon._sequence_timer.isActive())
        QApplication.sendEvent(bar.add_button, QEvent(QEvent.Type.Leave))
        self.assertFalse(plus_icon._sequence_timer.isActive())
        additions = []
        bar.custom_catalog_requested.connect(lambda: additions.append(True))
        bar.add_button.click()
        self.assertEqual(additions, [True])

        view = CatalogView()
        self.assertIsInstance(view.search, AnimatedSearchLineEdit)
        view.show()
        view.search.resize(240, 40)
        self.app.processEvents()
        QTest.mouseClick(
            view.search,
            Qt.MouseButton.LeftButton,
            pos=view.search.rect().center(),
        )
        self.assertTrue(view.search.hasFocus())
        view.search.setText("Doom")
        self.assertEqual(view.search.text(), "Doom")
        view.close()
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

    def test_my_velora_has_journey_entry_and_opens_canonical_card(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = UserRepository(Path(directory) / "user.db")
            page = ProfilePage(repository)
            game = next(
                item for item in load_catalog_items()
                if item.catalog_id == "g-shooter-fps-002"
            )
            game.status = "ПРОХОЖУ"
            page.refresh([game])
            labels = [
                page.tabs.tabText(index)
                for index in range(page.tabs.count())
            ]
            self.assertIn("JOURNEY", labels)
            self.assertEqual(page.journey_table.rowCount(), 1)
            opened = []
            page.journey_item_requested.connect(opened.append)
            page._open_link(page.journey_table, 0, 1)
            self.assertEqual(opened, [game.catalog_id])
            page.close()


if __name__ == "__main__":
    unittest.main()
