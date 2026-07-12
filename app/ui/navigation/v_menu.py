from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu


class VMenu(QMenu):
    placeholder_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.addSection("VELORA AW0.01")
        for title in (
            "Настройки", "Проверить обновления", "О проекте", "GitHub", "YouTube",
            "Поддержать Velora", "История изменений", "Дорожная карта", "Сообщить об ошибке",
        ):
            action = self.addAction(title)
            action.triggered.connect(self.placeholder_requested)
        self.addSeparator()
        self.addAction("Выход").triggered.connect(self._quit)

    @staticmethod
    def _quit() -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

