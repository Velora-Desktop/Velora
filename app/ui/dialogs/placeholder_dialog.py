from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout
from app.core.icon_registry import IconRegistry
from app.core.constants import APP_VERSION


class PlaceholderDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Velora {APP_VERSION}")
        self.setWindowIcon(IconRegistry.icon("info", variant="dark", category="feedback"))
        self.setModal(True)
        layout = QVBoxLayout(self)
        row = QHBoxLayout(); icon = QLabel(); icon.setFixedSize(42, 42); icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon.setPixmap(IconRegistry.pixmap("info", 36, variant="dark", category="feedback")); row.addWidget(icon)
        label = QLabel(f"Функция появится\nв одной из следующих версий Velora.\n\nТекущая версия: {APP_VERSION}")
        label.setMinimumWidth(340)
        row.addWidget(label); layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def show_placeholder(parent=None) -> None:
    PlaceholderDialog(parent).exec()
