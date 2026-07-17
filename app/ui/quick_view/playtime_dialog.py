from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.core.icon_registry import IconRegistry


class PlaytimeDialog(QDialog):
    def __init__(self, current_hours: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Общее игровое время")
        self.setWindowIcon(IconRegistry.icon("clock", variant="dark", category="ui"))
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        title = QLabel("ОБЩЕЕ ИГРОВОЕ ВРЕМЯ")
        title.setStyleSheet("font-size:15pt;font-weight:700;")
        root.addWidget(title)
        current_text = f"{current_hours:g} ч" if current_hours else "—"
        hint = QLabel(
            "Укажите суммарное время, проведённое в игре.\n"
            f"Сейчас сохранено: {current_text}"
        )
        hint.setObjectName("muted")
        root.addWidget(hint)

        counter = QHBoxLayout()
        counter.setSpacing(8)
        decrease = QPushButton("−")
        decrease.setToolTip("Уменьшить время на 0,5 часа")
        decrease.setFixedSize(42, 42)
        decrease.setStyleSheet("font-size:18pt;font-weight:600;")
        self.editor = QDoubleSpinBox()
        self.editor.setRange(0.0, 1_000_000.0)
        self.editor.setDecimals(1)
        self.editor.setSingleStep(0.5)
        self.editor.setSuffix(" ч")
        self.editor.setValue(max(0.0, float(current_hours)))
        self.editor.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.setMinimumHeight(42)
        self.editor.setStyleSheet("font-size:15pt;font-weight:650;")
        increase = QPushButton("+")
        increase.setToolTip("Увеличить время на 0,5 часа")
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

    def value(self) -> float:
        return self.editor.value()


def request_total_playtime(current_hours: float, parent=None) -> float | None:
    dialog = PlaytimeDialog(current_hours, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.value()
