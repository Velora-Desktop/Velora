from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QLabel, QVBoxLayout


def request_total_playtime(current_hours: float, parent=None) -> float | None:
    dialog = QDialog(parent); dialog.setWindowTitle("Общее игровое время")
    layout = QVBoxLayout(dialog)
    current_text = f"{current_hours:g} ч" if current_hours else "—"
    layout.addWidget(QLabel(f"Сколько часов вы наиграли всего?\nСейчас сохранено: {current_text}"))
    editor = QDoubleSpinBox(); editor.setRange(0.0, 10000.0); editor.setDecimals(1); editor.setSingleStep(0.5); editor.setSuffix(" ч"); editor.setValue(current_hours)
    layout.addWidget(editor)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить"); buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
    return editor.value() if dialog.exec() == QDialog.DialogCode.Accepted else None
