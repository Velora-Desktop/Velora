from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QSplitter, QVBoxLayout, QWidget

from app.styles.theme import application_stylesheet
from app.ui.catalog.catalog_view import CatalogView
from app.ui.dialogs.placeholder_dialog import show_placeholder
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.changelog_dialog import ChangelogDialog
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.dialogs.first_run_dialog import FirstRunDialog
from app.ui.navigation.top_bar import TopBar
from app.ui.quick_view.quick_view import QuickView
from app.ui.game_detail.game_detail_page import GameDetailPage
from app.ui.sidebar.sidebar import Sidebar
from app.data.user_repository import UserRepository
from app.ui.profile.profile_page import ProfilePage
from app.ui.search.search_page import SearchPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Velora AW0.08 · каталог AW0.0711")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(application_stylesheet())
        self.settings = QSettings("Velora", "Velora")
        self.user_repository = UserRepository()
        self.hide_adult_content = self.settings.value("content/hide_adult", True, type=bool)
        self.navigation_history = []
        self.navigation_index = -1
        self._navigating_history = False

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(5, 14, 12, 5)
        body.setSpacing(12)
        self.sidebar = Sidebar(CatalogView.category_counts())
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.addWidget(self.sidebar)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        self.catalog = CatalogView()
        self.user_repository.apply_game_states(self.catalog.items)
        for row in self.catalog.rows:
            row.sync_from_game()
        self.catalog.setObjectName("catalogPanel")
        self.catalog.set_hide_adult_content(self.hide_adult_content)
        self.quick_view = QuickView()
        self.quick_view.hide()
        self.game_detail = GameDetailPage()
        self.game_detail.hide()
        self.profile_page = ProfilePage(self.user_repository)
        self.profile_page.catalog_item_requested.connect(self.open_catalog_item)
        self.profile_page.hide()
        self.search_page = SearchPage()
        self.search_page.set_items(self.catalog.items)
        self.search_page.item_requested.connect(self.open_catalog_item)
        self.search_page.hide()
        self.empty_section = QLabel()
        self.empty_section.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_section.setStyleSheet("font-family:Georgia; font-size:24pt; color:#89949E;")
        self.empty_section.hide()
        center_layout.addWidget(self.catalog, 1)
        center_layout.addWidget(self.quick_view)
        center_layout.addWidget(self.game_detail, 1)
        center_layout.addWidget(self.profile_page, 1)
        center_layout.addWidget(self.search_page, 1)
        center_layout.addWidget(self.empty_section, 1)
        self.workspace_splitter.addWidget(center)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes((250, 1350))
        body.addWidget(self.workspace_splitter)
        root.addWidget(body_widget, 1)
        self.setCentralWidget(central)

        self.top_bar.placeholder_requested.connect(self._placeholder)
        self.top_bar.menu.settings_requested.connect(self._open_settings)
        self.top_bar.menu.about_requested.connect(self._open_about)
        self.top_bar.menu.changelog_requested.connect(self._open_changelog)
        self.top_bar.menu.support_requested.connect(self._open_support)
        self.top_bar.back_requested.connect(self._go_back)
        self.top_bar.forward_requested.connect(self._go_forward)
        self.top_bar.profile_requested.connect(self._open_profile)
        self.top_bar.section_requested.connect(self._on_section_selected)
        self.top_bar.search_requested.connect(self._open_global_search)
        self.sidebar.placeholder_requested.connect(self._placeholder)
        self.sidebar.category_selected.connect(self._on_category_selected)
        self.catalog.placeholder_requested.connect(self._placeholder)
        self.catalog.game_selected.connect(self._on_game_selected)
        self.catalog.status_changed.connect(self.quick_view.set_external_status)
        self.catalog.rating_requested.connect(self._rate_from_catalog)
        self.catalog.detail_requested.connect(self._on_detail_requested)
        self.catalog.hidden_requested.connect(self._hide_game)
        self.catalog.favorite_changed.connect(lambda game, value: self.user_repository.save_game_state(game))
        self.catalog.favorite_changed.connect(self.catalog.refresh_filters)
        self.quick_view.placeholder_requested.connect(self._placeholder)
        self.quick_view.status_changed.connect(self.catalog.set_game_status)
        self.quick_view.rating_changed.connect(self.catalog.set_game_score)
        self.quick_view.favorite_changed.connect(self.catalog.refresh_filters)
        self.quick_view.favorite_changed.connect(lambda game, value: self.user_repository.save_game_state(game))
        self.quick_view.status_changed.connect(lambda game, value: self.user_repository.save_game_state(game))
        self.quick_view.rating_changed.connect(lambda game, value: self.user_repository.save_game_state(game))
        self.quick_view.playtime_changed.connect(lambda game, value: self.user_repository.save_game_state(game))
        self.quick_view.detail_requested.connect(self._on_detail_requested)
        self.quick_view.hidden_requested.connect(self._hide_game)
        self.game_detail.favorite_changed.connect(self.catalog.refresh_filters)
        self.game_detail.rate_requested.connect(self._rate_from_detail)
        self.game_detail.status_changed.connect(self.catalog.set_game_status)
        self.game_detail.status_changed.connect(lambda game, value: self.user_repository.save_game_state(game))
        self.game_detail.status_changed.connect(self.quick_view.set_external_status)
        self.game_detail.favorite_changed.connect(lambda game, value: self.user_repository.save_game_state(game))

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._open_global_search)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.quick_view.hide)
        self._push_navigation(("category", ("Игры", "ШУТЕРЫ")))
        self._run_first_launch_if_needed()

    def _run_first_launch_if_needed(self) -> None:
        if self.settings.value("onboarding/completed", False, type=bool):
            return
        # Content stays hidden unless the user explicitly completes the dialog
        # and chooses to show it.
        self.hide_adult_content = True
        self.catalog.set_hide_adult_content(True)
        dialog = FirstRunDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        profile = self.user_repository.load_profile()
        profile.display_name = dialog.display_name
        self.user_repository.save_profile(profile)
        self._set_hide_adult_content(dialog.hide_adult_content)
        self.settings.setValue("onboarding/profile_created", dialog.profile_requested)
        self.settings.setValue("onboarding/completed", True)

    def _placeholder(self) -> None:
        show_placeholder(self)

    def _on_game_selected(self, game) -> None:
        self.empty_section.hide()
        self.top_bar.set_profile_active(False)
        self.top_bar.set_search_active(False)
        self.sidebar.show()
        self.profile_page.hide()
        self.search_page.hide()
        self.game_detail.hide()
        self.catalog.show()
        self.quick_view.set_game(game)
        if not self._navigating_history:
            self._push_navigation(("game", game.catalog_id))
        self._update_history_buttons()

    def _on_category_selected(self, category: str) -> None:
        self.empty_section.hide()
        self.top_bar.set_profile_active(False)
        self.top_bar.set_search_active(False)
        self.sidebar.show()
        self.profile_page.hide()
        self.search_page.hide()
        self.game_detail.hide()
        self.catalog.show()
        self.catalog.set_category(category)
        self.quick_view.hide()
        if not self._navigating_history:
            self._push_navigation(("category", (self.catalog.current_media_type, category)))

    def _on_detail_requested(self, game) -> None:
        self.top_bar.set_active_space(game.media_type.upper())
        self.top_bar.set_search_active(False)
        self.sidebar.show()
        self.catalog.set_media_type(game.media_type, game.category)
        self.sidebar.set_categories(self.catalog.categories_for(game.media_type))
        self.sidebar.select_category(game.category.upper())
        if not self._navigating_history:
            self._push_navigation(("detail", game.catalog_id))
        self.game_detail.set_game(game)
        self._show_center_page(self.game_detail)

    def _show_profile(self) -> None:
        self.top_bar.set_profile_active(True)
        self.profile_page.refresh(self.catalog.items)
        self.sidebar.hide()
        self.catalog.hide(); self.quick_view.hide(); self.game_detail.hide(); self.search_page.hide(); self.empty_section.hide(); self.profile_page.show()

    def _show_center_page(self, page) -> None:
        """Guarantee that central workspaces never overlap in the layout."""
        for widget in (self.catalog, self.quick_view, self.game_detail, self.profile_page, self.search_page, self.empty_section):
            widget.setVisible(widget is page)

    def open_catalog_item(self, catalog_id: str) -> None:
        """Resolve a stable catalog link and open its canonical detail page."""
        game = self._catalog_row(catalog_id)
        if game is None:
            return
        self._on_detail_requested(game)

    def _catalog_row(self, catalog_id: str):
        """Resolve an official catalog object by its stable database ID."""
        return next((game for game in self.catalog.items if game.catalog_id == catalog_id), None)

    def _restore_catalog_context(self, catalog_id: str):
        """Restore the section and category from catalog data."""
        game = self._catalog_row(catalog_id)
        if game is None:
            return None
        self.top_bar.set_active_space(game.media_type.upper())
        self.top_bar.set_profile_active(False)
        self.sidebar.show()
        self.catalog.set_media_type(game.media_type, game.category)
        self.sidebar.set_categories(self.catalog.categories_for(game.media_type))
        self.sidebar.select_category(game.category.upper())
        return game

    def _on_section_selected(self, section: str) -> None:
        if not self._navigating_history:
            self._push_navigation(("section", section))
        self.top_bar.set_active_space(section)
        self.top_bar.set_search_active(False)
        self.profile_page.hide(); self.search_page.hide(); self.game_detail.hide(); self.quick_view.hide(); self.empty_section.hide()
        media_type = {"ИГРЫ": "Игры", "ФИЛЬМЫ": "Фильмы", "СЕРИАЛЫ": "Сериалы", "ПРОГРАММЫ": "Программы"}.get(section)
        if media_type:
            self.catalog.set_media_type(media_type)
            self.sidebar.set_categories(self.catalog.categories_for(media_type))
            self.sidebar.show(); self.catalog.show()
            if self.catalog.current_category:
                self.sidebar.select_category(self.catalog.current_category)

    def _push_navigation(self, entry: tuple[str, object]) -> None:
        if self.navigation_index >= 0 and self.navigation_history[self.navigation_index] == entry:
            self._update_history_buttons()
            return
        self.navigation_history = self.navigation_history[: self.navigation_index + 1]
        self.navigation_history.append(entry)
        self.navigation_index = len(self.navigation_history) - 1
        self._update_history_buttons()

    def _go_back(self) -> None:
        if self.navigation_index <= 0:
            return
        self.navigation_index -= 1
        self._navigate_to_history_item()

    def _go_forward(self) -> None:
        if self.navigation_index >= len(self.navigation_history) - 1:
            return
        self.navigation_index += 1
        self._navigate_to_history_item()

    def _navigate_to_history_item(self) -> None:
        self._navigating_history = True
        try:
            kind, value = self.navigation_history[self.navigation_index]
            if kind == "category":
                media_type, category = value if isinstance(value, tuple) else ("Игры", value)
                self.empty_section.hide()
                self.top_bar.set_profile_active(False)
                self.sidebar.show()
                self.profile_page.hide()
                self.game_detail.hide()
                self.catalog.show()
                self.catalog.set_media_type(media_type, category)
                self.sidebar.set_categories(self.catalog.categories_for(media_type))
                self.sidebar.select_category(category)
                self.quick_view.hide()
            elif kind == "game":
                self.empty_section.hide()
                self.profile_page.hide()
                self.game_detail.hide()
                self.catalog.show()
                game = self._restore_catalog_context(value)
                if game is not None: self.catalog.select_game(game)
            elif kind == "detail":
                self.empty_section.hide()
                self.profile_page.hide()
                self.open_catalog_item(value)
            elif kind == "profile":
                self._show_profile()
            elif kind == "search":
                self._open_global_search()
            elif kind == "section":
                self._on_section_selected(value)
        finally:
            self._navigating_history = False
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        self.top_bar.back_button.setEnabled(self.navigation_index > 0)
        self.top_bar.forward_button.setEnabled(
            0 <= self.navigation_index < len(self.navigation_history) - 1
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.hide_adult_content, self.catalog.items, self)
        dialog.adult_filter_changed.connect(self._set_hide_adult_content)
        dialog.hidden_restored.connect(self._restore_hidden_game)
        dialog.profile_reset_requested.connect(self._reset_local_profile)
        dialog.exec()

    def _restore_hidden_game(self, game) -> None:
        self.user_repository.save_game_state(game); self.catalog.refresh_filters()

    def _reset_local_profile(self) -> None:
        self.user_repository.reset_local_profile()
        self.settings.remove("onboarding")
        self.settings.setValue("content/hide_adult", True)
        QMessageBox.information(self, "Velora", "Локальный профиль сброшен.\nПри следующем запуске откроется мастер первого запуска.")
        QApplication.quit()

    def _set_hide_adult_content(self, enabled: bool) -> None:
        self.hide_adult_content = enabled
        self.settings.setValue("content/hide_adult", enabled)
        self.catalog.set_hide_adult_content(enabled)

    def _open_about(self) -> None:
        AboutDialog(self).exec()

    def _open_changelog(self) -> None:
        ChangelogDialog(self).exec()

    def _open_profile(self) -> None:
        if not self._navigating_history:
            self._push_navigation(("profile", None))
        self._show_profile()

    def _open_global_search(self) -> None:
        if not self._navigating_history:
            self._push_navigation(("search", None))
        self.top_bar.set_profile_active(False)
        self.top_bar.set_search_active(True)
        self.sidebar.hide()
        self.search_page.set_items(self.catalog.items)
        self._show_center_page(self.search_page)
        self.search_page.focus_search()

    def _rate_from_detail(self, game) -> None:
        # The rating editor is shared with Quick View, but opening it from the
        # full page must not make the Quick View panel visible underneath.
        self.quick_view.current_game = game
        self.quick_view._open_rating_dialog()
        self.quick_view.hide()
        self.game_detail.set_game(game)
        self.game_detail.show()

    def _rate_from_catalog(self, game) -> None:
        self.quick_view.current_game = game
        self.quick_view._open_rating_dialog()
        self.quick_view.hide()

    def _hide_game(self, game) -> None:
        game.hidden = True
        self.user_repository.save_game_state(game)
        self.quick_view.hide()
        self.catalog.refresh_filters()

    @staticmethod
    def _open_support() -> None:
        QDesktopServices.openUrl(QUrl("https://boosty.to/cho_pik"))
