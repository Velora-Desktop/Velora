from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class PlaceholderDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Velora AW0.01")
        self.setModal(True)
        layout = QVBoxLayout(self)
        label = QLabel("Функция появится\nв одной из следующих версий Velora.\n\nТекущая версия: AW0.01")
        label.setMinimumWidth(340)
        layout.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def show_placeholder(parent=None) -> None:
    PlaceholderDialog(parent).exec()

