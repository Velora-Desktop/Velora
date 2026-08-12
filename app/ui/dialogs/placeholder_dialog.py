from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout
from app.core.constants import APP_VERSION
from app.ui.velora_ui.components import HoverAnimatedIcon
from app.ui.velora_ui.icons import IconProvider


class PlaceholderDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Velora {APP_VERSION}")
        self.setWindowIcon(IconProvider.icon("animated.info", 20))
        self.setModal(True)
        layout = QVBoxLayout(self)
        row = QHBoxLayout(); icon = HoverAnimatedIcon(
            "animated.info", 36, autoplay=True, frame_interval_ms=41,
            mouse_transparent=True,
        )
        icon.setObjectName("placeholderAnimatedInfoIcon")
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        label = QLabel(f"Функция появится\nв одной из следующих версий Velora.\n\nТекущая версия: {APP_VERSION}")
        label.setMinimumWidth(340)
        row.addWidget(label); layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def show_placeholder(parent=None) -> None:
    PlaceholderDialog(parent).exec()
