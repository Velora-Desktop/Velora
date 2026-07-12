from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from app.styles.theme import application_stylesheet
from app.ui.catalog.catalog_view import CatalogView
from app.ui.dialogs.placeholder_dialog import show_placeholder
from app.ui.navigation.top_bar import TopBar
from app.ui.quick_view.quick_view import QuickView
from app.ui.sidebar.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Velora AW0.01")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(application_stylesheet())

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar()
        body.addWidget(self.sidebar)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self.catalog = CatalogView()
        self.quick_view = QuickView()
        self.quick_view.hide()
        center_layout.addWidget(self.catalog, 1)
        center_layout.addWidget(self.quick_view)
        body.addWidget(center, 1)
        root.addLayout(body, 1)
        self.setCentralWidget(central)

        self.top_bar.placeholder_requested.connect(self._placeholder)
        self.sidebar.placeholder_requested.connect(self._placeholder)
        self.catalog.placeholder_requested.connect(self._placeholder)
        self.catalog.game_selected.connect(self.quick_view.set_game)
        self.quick_view.placeholder_requested.connect(self._placeholder)

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._placeholder)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.quick_view.hide)

    def _placeholder(self) -> None:
        show_placeholder(self)
