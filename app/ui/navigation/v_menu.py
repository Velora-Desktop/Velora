from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu


class VMenu(QMenu):
    settings_requested = Signal()
    about_requested = Signal()
    changelog_requested = Signal()
    support_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.addSection("VELORA AW0.04")
        self.addAction("Настройки").triggered.connect(self.settings_requested)
        self.addAction("О проекте").triggered.connect(self.about_requested)
        self.addAction("История изменений").triggered.connect(self.changelog_requested)
        self.addAction("Поддержать Velora").triggered.connect(self.support_requested)
        self.addSeparator()
        self.addAction("Выход").triggered.connect(self._quit)

    @staticmethod
    def _quit() -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
