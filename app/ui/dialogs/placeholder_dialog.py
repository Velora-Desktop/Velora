from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout
from app.core.icon_registry import IconRegistry


class PlaceholderDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Velora AW0.07")
        self.setWindowIcon(IconRegistry.icon("info", variant="dark", category="feedback"))
        self.setModal(True)
        layout = QVBoxLayout(self)
        row = QHBoxLayout(); icon = QLabel(); icon.setFixedSize(42, 42); icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon.setPixmap(IconRegistry.pixmap("info", 36, variant="dark", category="feedback")); row.addWidget(icon)
        label = QLabel("Функция появится\nв одной из следующих версий Velora.\n\nТекущая версия: AW0.07")
        label.setMinimumWidth(340)
        row.addWidget(label); layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def show_placeholder(parent=None) -> None:
    PlaceholderDialog(parent).exec()
