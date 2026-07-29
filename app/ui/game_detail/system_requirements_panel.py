from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget


REQUIREMENT_ROWS = (
    ("os", "ОС"),
    ("cpu", "Процессор"),
    ("ram", "Память"),
    ("storage", "Место на диске"),
    ("gpu", "Видеокарта"),
    ("additional", "Дополнительно"),
)


class SystemRequirementsPanel(QFrame):
    """Standalone two-column requirements section used by game details."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("systemRequirementsSection")
        self.setStyleSheet(
            "QFrame#systemRequirementsSection {"
            "background:#101820;border:1px solid #2A3640;border-radius:4px;}"
            "QFrame#systemRequirementsSection QWidget {background:transparent;}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 22)
        root.setSpacing(14)
        title = QLabel("Системные требования")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:18pt;font-weight:700;color:#F4F5F7;")
        root.addWidget(title)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color:#34414A;")
        root.addWidget(divider)

        columns = QGridLayout()
        columns.setHorizontalSpacing(46)
        columns.setVerticalSpacing(8)
        self._sections: dict[str, tuple[QWidget, dict[str, QLabel]]] = {}
        for column, (suffix, heading) in enumerate(
            (("min", "Минимальные"), ("rec", "Рекомендуемые"))
        ):
            container = QWidget()
            container.setObjectName(f"requirements_{suffix}")
            container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            container.setStyleSheet("background:transparent;border:0;")
            layout = QGridLayout(container)
            layout.setContentsMargins(0, 4, 0, 0)
            layout.setHorizontalSpacing(16)
            layout.setVerticalSpacing(8)
            section_title = QLabel(heading)
            section_title.setStyleSheet("font-size:11pt;font-weight:700;color:#F2F4F7;")
            layout.addWidget(section_title, 0, 0, 1, 2)
            values: dict[str, QLabel] = {}
            for row, (key, caption) in enumerate(REQUIREMENT_ROWS, 1):
                label = QLabel(caption)
                label.setStyleSheet("color:#8494A2;")
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                value = QLabel()
                value.setWordWrap(True)
                value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                value.setStyleSheet("color:#F0F2F5;font-weight:500;")
                layout.addWidget(label, row, 0)
                layout.addWidget(value, row, 1)
                values[key] = value
            layout.setColumnStretch(1, 1)
            columns.addWidget(container, 0, column)
            columns.setColumnStretch(column, 1)
            self._sections[suffix] = (container, values)
        root.addLayout(columns)
        self.setVisible(False)

    def set_requirements(self, requirements: dict[str, str], *, visible: bool) -> None:
        requirements = requirements or {}
        any_value = False
        for suffix, (container, values) in self._sections.items():
            section_has_values = False
            for key, label in values.items():
                raw_value = requirements.get(f"{key}_{suffix}", "")
                if key == "storage" and suffix == "min" and not raw_value:
                    raw_value = requirements.get("storage", "")
                text = str(raw_value or "").strip()
                label.setText(text or "—")
                section_has_values = section_has_values or bool(text)
            container.setVisible(section_has_values)
            any_value = any_value or section_has_values
        self.setVisible(visible and any_value)
