from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import ACCENT


class Sidebar(QFrame):
    placeholder_requested = Signal()

    CATEGORIES = (
        ("⌖", "Шутеры"), ("⚔", "Экшен"), ("◆", "RPG"), ("⌁", "Приключения"),
        ("◉", "Гонки"), ("♜", "Стратегии"), ("◇", "Хорроры"), ("◎", "MMO"),
        ("拳", "Файтинги"), ("◌", "Спортивные"), ("▦", "Головоломки"), ("▣", "Аркады"),
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setMinimumWidth(190)
        self.setMaximumWidth(300)
        self.setFixedWidth(230)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 14, 10, 10)
        title = QLabel("ИГРЫ")
        title.setObjectName("muted")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        categories = QVBoxLayout(content)
        categories.setContentsMargins(0, 8, 0, 8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, (icon, text) in enumerate(self.CATEGORIES):
            button = QPushButton(f"{icon}   {text}")
            button.setCheckable(True)
            button.setProperty("category", True)
            button.setStyleSheet(
                f"QPushButton {{ text-align:left; padding:9px; }}"
                f"QPushButton:checked {{ color:{ACCENT}; border-left:3px solid {ACCENT}; background:#211D31; }}"
            )
            button.setChecked(index == 0)
            group.addButton(button)
            categories.addWidget(button)
        categories.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        for text in ("+ Добавить жанр", "+ Добавить свою игру"):
            button = QPushButton(text)
            button.clicked.connect(self.placeholder_requested)
            root.addWidget(button)

