from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.data.personal_library_repository import PersonalLibraryRepository
from app.data.user_repository import UserRepository
from app.ui.profile.personal_library_page import PersonalLibraryPage
from app.ui.profile.planning_page import PlanningPage


class AssistantPage(QWidget):
    """Compact entry point for the existing personal-library helpers."""

    catalog_item_requested = Signal(str)

    def __init__(self, repository: UserRepository, parent=None) -> None:
        super().__init__(parent)
        self.planning_repository = PersonalLibraryRepository(repository.path)
        self.planning = PlanningPage(self.planning_repository)
        self.library = PersonalLibraryPage(repository)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs)

        helper = self.planning.widget(0)
        self.planning.removeTab(0)
        library_pages = {
            self.library.tabs.tabText(index): self.library.tabs.widget(index)
            for index in range(self.library.tabs.count())
        }
        for page in library_pages.values():
            self.library.tabs.removeTab(self.library.tabs.indexOf(page))

        self.tabs.addTab(helper, "ПОМОЩНИК")
        for title in ("УМНЫЕ СПИСКИ", "ЦЕЛИ", "ТЕГИ", "АНАЛИТИКА ВКУСА"):
            self.tabs.addTab(library_pages[title], title)

        self.planning.catalog_item_requested.connect(self.catalog_item_requested.emit)
        self.library.catalog_item_requested.connect(self.catalog_item_requested.emit)

    def refresh(self, items) -> None:
        self.planning.refresh(items)
        self.library.refresh(items)
