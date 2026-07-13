from PySide6.QtWidgets import QDialog, QDialogButtonBox, QGridLayout, QLabel, QSpinBox, QVBoxLayout


CRITERIA = ("Графика", "Саундтрек", "Сюжет", "Геймплей", "Атмосфера")


def request_rating(current: dict[str, int], parent=None) -> dict[str, int] | None:
    dialog = QDialog(parent); dialog.setWindowTitle("Моя оценка")
    layout = QVBoxLayout(dialog)
    intro = QLabel("Оцените каждый критерий от 1 до 10.\nИтог — среднее арифметическое пяти значений.")
    intro.setWordWrap(True); layout.addWidget(intro)
    form = QGridLayout(); editors = {}
    for row, criterion in enumerate(CRITERIA):
        form.addWidget(QLabel(criterion), row, 0); editor = QSpinBox(); editor.setRange(1, 10)
        editor.setValue(current.get(criterion, 5)); editor.setSuffix(" / 10"); editors[criterion] = editor; form.addWidget(editor, row, 1)
    layout.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Save).setText("Рассчитать и сохранить")
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted: return None
    return {name: editor.value() for name, editor in editors.items()}
