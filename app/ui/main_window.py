from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from app.styles.theme import application_stylesheet
from app.ui.catalog.catalog_view import CatalogView
from app.ui.dialogs.placeholder_dialog import show_placeholder
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.changelog_dialog import ChangelogDialog
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.navigation.top_bar import TopBar
from app.ui.quick_view.quick_view import QuickView
from app.ui.sidebar.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Velora AW0.02")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(application_stylesheet())
        self.settings = QSettings("Velora", "Velora")
        self.hide_adult_content = self.settings.value("content/hide_adult", False, type=bool)
        self.navigation_history = []
        self.navigation_index = -1
        self._navigating_history = False

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(5, 14, 12, 5)
        body.setSpacing(12)
        self.sidebar = Sidebar(CatalogView.category_counts())
        body.addWidget(self.sidebar)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        self.catalog = CatalogView()
        self.catalog.setObjectName("catalogPanel")
        self.catalog.set_hide_adult_content(self.hide_adult_content)
        self.quick_view = QuickView()
        self.quick_view.hide()
        center_layout.addWidget(self.catalog, 1)
        center_layout.addWidget(self.quick_view)
        body.addWidget(center, 1)
        root.addLayout(body, 1)
        self.setCentralWidget(central)

        self.top_bar.placeholder_requested.connect(self._placeholder)
        self.top_bar.menu.settings_requested.connect(self._open_settings)
        self.top_bar.menu.about_requested.connect(self._open_about)
        self.top_bar.menu.changelog_requested.connect(self._open_changelog)
        self.top_bar.menu.support_requested.connect(self._open_support)
        self.top_bar.back_requested.connect(self._go_back)
        self.top_bar.forward_requested.connect(self._go_forward)
        self.sidebar.placeholder_requested.connect(self._placeholder)
        self.sidebar.category_selected.connect(self._on_category_selected)
        self.catalog.placeholder_requested.connect(self._placeholder)
        self.catalog.game_selected.connect(self._on_game_selected)
        self.catalog.status_changed.connect(self.quick_view.set_external_status)
        self.quick_view.placeholder_requested.connect(self._placeholder)
        self.quick_view.status_changed.connect(self.catalog.set_game_status)
        self.quick_view.rating_changed.connect(self.catalog.set_game_score)
        self.quick_view.favorite_changed.connect(self.catalog.refresh_filters)
        self.quick_view.detail_requested.connect(self._on_detail_requested)

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._placeholder)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.quick_view.hide)
        self._push_navigation(("category", "ШУТЕРЫ"))

    def _placeholder(self) -> None:
        show_placeholder(self)

    def _on_game_selected(self, game) -> None:
        self.quick_view.set_game(game)
        if not self._navigating_history:
            self._push_navigation(("game", game))
        self._update_history_buttons()

    def _on_category_selected(self, category: str) -> None:
        self.catalog.set_category(category)
        self.quick_view.hide()
        if not self._navigating_history:
            self._push_navigation(("category", category))

    def _on_detail_requested(self, game) -> None:
        self._push_navigation(("detail", game))
        self._placeholder()

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
                self.sidebar.select_category(value)
                self.catalog.set_category(value)
                self.quick_view.hide()
            elif kind == "game":
                self.sidebar.select_category("ШУТЕРЫ")
                self.catalog.set_category("ШУТЕРЫ")
                self.catalog.select_game(value)
            elif kind == "detail":
                self.sidebar.select_category("ШУТЕРЫ")
                self.catalog.set_category("ШУТЕРЫ")
                self.catalog.select_game(value)
                self._placeholder()
        finally:
            self._navigating_history = False
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        self.top_bar.back_button.setEnabled(self.navigation_index > 0)
        self.top_bar.forward_button.setEnabled(
            0 <= self.navigation_index < len(self.navigation_history) - 1
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.hide_adult_content, self)
        dialog.adult_filter_changed.connect(self._set_hide_adult_content)
        dialog.exec()

    def _set_hide_adult_content(self, enabled: bool) -> None:
        self.hide_adult_content = enabled
        self.settings.setValue("content/hide_adult", enabled)
        self.catalog.set_hide_adult_content(enabled)

    def _open_about(self) -> None:
        AboutDialog(self).exec()

    def _open_changelog(self) -> None:
        ChangelogDialog(self).exec()

    @staticmethod
    def _open_support() -> None:
        QDesktopServices.openUrl(QUrl("https://boosty.to/cho_pik"))
