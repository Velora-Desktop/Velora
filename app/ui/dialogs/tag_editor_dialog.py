"""Editor for personal tags only."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from app.application.tag_service import normalize_tag


class TagEditorDialog(QDialog):
    def __init__(self, tags: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Мои теги")
        self.setMinimumWidth(480)
        self._tags = list(tags)
        root = QVBoxLayout(self)
        title = QLabel("МОИ ТЕГИ")
        title.setStyleSheet("font-size:16pt;font-weight:700;")
        root.addWidget(title)
        add_row = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Новый тег")
        self.name.returnPressed.connect(self._add)
        add_row.addWidget(self.name, 1)
        add = QPushButton("ДОБАВИТЬ")
        add.clicked.connect(self._add)
        add_row.addWidget(add)
        root.addLayout(add_row)
        self.list = QVBoxLayout()
        root.addLayout(self.list)
        root.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("СОХРАНИТЬ")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("ОТМЕНА")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._render()

    def tags(self) -> list[str]:
        return list(self._tags)

    def _add(self) -> None:
        value = normalize_tag(self.name.text())
        if not value or value.casefold() in {tag.casefold() for tag in self._tags}:
            return
        self._tags.append(value)
        self.name.clear()
        self._render()

    def _render(self) -> None:
        while self.list.count():
            item = self.list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for tag in self._tags:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 2, 0, 2)
            label = QLabel(f"#{tag}")
            layout.addWidget(label, 1)
            remove = QPushButton("УДАЛИТЬ")
            remove.setCursor(Qt.CursorShape.PointingHandCursor)
            remove.clicked.connect(
                lambda checked=False, value=tag: self._remove(value)
            )
            layout.addWidget(remove)
            self.list.addWidget(row)

    def _remove(self, value: str) -> None:
        self._tags = [tag for tag in self._tags if tag != value]
        self._render()
