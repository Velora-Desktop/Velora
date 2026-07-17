from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from app.core.icon_registry import IconRegistry


class WatchCountDialog(QDialog):
    def __init__(self, current: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Просмотры")
        self.setWindowIcon(IconRegistry.icon("eye", category="ui"))
        self.setMinimumWidth(390)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        title = QLabel("КОЛИЧЕСТВО ПРОСМОТРОВ")
        title.setStyleSheet("font-size:15pt;font-weight:700;")
        root.addWidget(title)
        hint = QLabel("Укажите, сколько раз вы полностью посмотрели фильм.")
        hint.setObjectName("muted")
        root.addWidget(hint)

        counter = QHBoxLayout()
        counter.setSpacing(8)
        decrease = QPushButton("−")
        decrease.setToolTip("Уменьшить количество просмотров")
        decrease.setFixedSize(42, 42)
        decrease.setStyleSheet("font-size:18pt;font-weight:600;")
        self.editor = QSpinBox()
        self.editor.setRange(0, 999)
        self.editor.setValue(max(0, int(current)))
        self.editor.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.setMinimumHeight(42)
        self.editor.setStyleSheet("font-size:15pt;font-weight:650;")
        increase = QPushButton("+")
        increase.setToolTip("Увеличить количество просмотров")
        increase.setFixedSize(42, 42)
        increase.setStyleSheet("font-size:16pt;font-weight:600;")
        decrease.clicked.connect(self.editor.stepDown)
        increase.clicked.connect(self.editor.stepUp)
        counter.addWidget(decrease)
        counter.addWidget(self.editor, 1)
        counter.addWidget(increase)
        root.addLayout(counter)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("ОТМЕНА")
        cancel.clicked.connect(self.reject)
        save = QPushButton("СОХРАНИТЬ")
        save.setProperty("primary", True)
        save.setIcon(IconRegistry.icon("save", category="ui"))
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)

    def value(self) -> int:
        return self.editor.value()


def request_watch_count(current: int, parent=None) -> int | None:
    dialog = WatchCountDialog(current, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.value()
