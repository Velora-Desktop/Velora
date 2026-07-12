from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QDialog, QLabel, QVBoxLayout


class SettingsDialog(QDialog):
    adult_filter_changed = Signal(bool)

    def __init__(self, hide_adult_content: bool, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки Velora")
        self.setModal(True)
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        title = QLabel("НАСТРОЙКИ")
        title.setStyleSheet("font-size:16pt; font-weight:600;")
        root.addWidget(title)

        description = QLabel(
            "Управление отображением материалов с возрастным ограничением.\n"
            "Настройка хранится только на этом компьютере."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)
        root.addWidget(description)

        self.adult_filter = QCheckBox("Скрывать непристойный контент и карточки 18+")
        self.adult_filter.setChecked(hide_adult_content)
        self.adult_filter.setMinimumHeight(44)
        self.adult_filter.toggled.connect(self.adult_filter_changed)
        root.addWidget(self.adult_filter)

        state_hint = QLabel(
            "Выключено — показывается весь каталог.\n"
            "Включено — объекты с рейтингом 18+ скрываются из каталога и поиска."
        )
        state_hint.setObjectName("muted")
        state_hint.setWordWrap(True)
        root.addWidget(state_hint)
