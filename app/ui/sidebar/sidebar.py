from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import ACCENT


class Sidebar(QFrame):
    placeholder_requested = Signal()
    category_selected = Signal(str)

    CATEGORIES = (
        ("crosshair", "ШУТЕРЫ"), ("compass", "ПРИКЛЮЧЕНИЕ"), ("race", "ГОНКИ"),
        ("helmet", "RPG"), ("strategy", "СТРАТЕГИИ"), ("sport", "СПОРТ"),
        ("fist", "ФАЙТИНГИ"), ("skull", "ХОРРОРЫ"), ("gear", "СИМУЛЯТОРЫ"),
        ("platform", "ПЛАТФОРМЕРЫ"), ("puzzle", "ГОЛОВОЛОМКИ"), ("globe", "MMO"),
    )

    def __init__(self, category_counts: dict[str, int] | None = None, parent=None) -> None:
        super().__init__(parent)
        category_counts = category_counts or {}
        self.setObjectName("panel")
        self.setMinimumWidth(210)
        self.setMaximumWidth(260)
        self.setFixedWidth(240)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 14, 10, 10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        categories = QVBoxLayout(content)
        categories.setContentsMargins(0, 8, 0, 8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.category_buttons: dict[str, QPushButton] = {}
        icons_dir = __import__("pathlib").Path(__file__).resolve().parents[3] / "assets" / "icons" / "genres"
        for index, (icon_name, text) in enumerate(self.CATEGORIES):
            count = category_counts.get(text, 0)
            row = QFrame()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 4, 0)
            row_layout.setSpacing(2)
            button = QPushButton(text)
            button.setIcon(QIcon(str(icons_dir / f"{icon_name}.svg")))
            button.setIconSize(__import__("PySide6.QtCore", fromlist=["QSize"]).QSize(18, 18))
            button.setCheckable(True)
            button.setProperty("category", True)
            button.setStyleSheet(
                f"QPushButton {{ font-family:'Segoe UI'; font-size:10pt; text-align:left; padding:9px 8px; color:#D8DCE0; }}"
                f"QPushButton:checked {{ color:white; border-left:3px solid {ACCENT}; background:#6A20C8; }}"
            )
            button.setChecked(index == 0)
            group.addButton(button)
            self.category_buttons[text] = button
            button.clicked.connect(lambda checked=False, name=text: self.category_selected.emit(name))
            row_layout.addWidget(button, 1)
            count_label = QLabel(str(count))
            count_label.setFixedWidth(32)
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet("color:#C8CDD2; background:#0A1016; border:1px solid #1C2730; border-radius:4px; padding:2px;")
            row_layout.addWidget(count_label)
            categories.addWidget(row)
        categories.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        for text in ("＋  ДОБАВИТЬ КАТЕГОРИЮ", "＋  ДОБАВИТЬ СВОЮ ИГРУ"):
            button = QPushButton(text)
            button.setMinimumHeight(44)
            if "КАТЕГОРИЮ" in text:
                button.setStyleSheet(f"color:#B56CFF; border:1px solid {ACCENT}; text-align:left;")
            else:
                button.setStyleSheet("border:1px solid #28343D; text-align:left;")
            button.clicked.connect(self.placeholder_requested)
            root.addWidget(button)

    def select_category(self, category: str, emit_signal: bool = False) -> None:
        button = self.category_buttons.get(category)
        if button is None:
            return
        button.setChecked(True)
        if emit_signal:
            self.category_selected.emit(category)
