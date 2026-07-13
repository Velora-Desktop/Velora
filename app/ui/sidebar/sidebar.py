from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import ACCENT


ICON_BY_CATEGORY = {
    "ШУТЕРЫ": "crosshair", "ПРИКЛЮЧЕНИЯ": "compass", "ГОНКИ": "race", "RPG": "helmet",
    "СТРАТЕГИИ": "strategy", "СПОРТИВНЫЕ": "sport", "ФАЙТИНГИ": "fist", "УЖАСЫ": "skull",
    "СИМУЛЯТОРЫ": "gear", "ПЛАТФОРМЕРЫ": "platform", "ГОЛОВОЛОМКИ": "puzzle", "MMO": "globe",
    "ДРАМА": "compass", "ФАНТАСТИКА": "globe", "БОЕВИК": "fist", "КОМЕДИЯ": "sport",
    "АНИМАЦИЯ": "puzzle", "ДЕТЕКТИВ": "crosshair", "УЖАСЫ": "skull", "ФЭНТЕЗИ": "helmet",
    "ОПЕРАЦИОННЫЕ СИСТЕМЫ": "gear", "СИСТЕМНЫЕ": "gear", "ОФИСНЫЕ": "platform",
    "ГРАФИКА": "puzzle", "ВИДЕО": "compass", "АУДИО": "sport", "РАЗРАБОТКА": "strategy",
    "БЕЗОПАСНОСТЬ": "helmet", "ИНТЕРНЕТ": "globe",
}


class Sidebar(QFrame):
    placeholder_requested = Signal()
    category_selected = Signal(str)

    def __init__(self, category_counts: dict[str, int] | None = None, parent=None) -> None:
        super().__init__(parent); self.setObjectName("panel"); self.setFixedWidth(240)
        self.root = QVBoxLayout(self); self.root.setContentsMargins(10,14,10,10)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.root.addWidget(self.scroll,1)
        self.add_category = QPushButton("＋  ДОБАВИТЬ КАТЕГОРИЮ"); self.add_item = QPushButton("＋  ДОБАВИТЬ СВОЙ ОБЪЕКТ")
        self.add_category.setMinimumHeight(44); self.add_item.setMinimumHeight(44)
        self.add_category.setStyleSheet(f"color:#B56CFF;border:1px solid {ACCENT};text-align:left;")
        self.add_item.setStyleSheet("border:1px solid #28343D;text-align:left;")
        self.add_category.clicked.connect(self.placeholder_requested); self.add_item.clicked.connect(self.placeholder_requested)
        self.root.addWidget(self.add_category); self.root.addWidget(self.add_item)
        self.category_buttons: dict[str,QPushButton] = {}; self.set_categories(category_counts or {})

    def set_categories(self, category_counts: dict[str, int]) -> None:
        content=QWidget(); layout=QVBoxLayout(content); layout.setContentsMargins(0,8,0,8)
        self.group=QButtonGroup(self); self.group.setExclusive(True); self.category_buttons={}
        icons=Path(__file__).resolve().parents[3]/"assets"/"icons"/"genres"
        for index,(category,count) in enumerate(category_counts.items()):
            row=QFrame(); rl=QHBoxLayout(row); rl.setContentsMargins(0,0,4,0); rl.setSpacing(2)
            button=QPushButton(category); icon_name=ICON_BY_CATEGORY.get(category,"globe"); button.setIcon(QIcon(str(icons/f"{icon_name}.svg"))); button.setIconSize(QSize(18,18)); button.setCheckable(True); button.setProperty("category",True)
            button.setStyleSheet(f"QPushButton{{font-size:10pt;text-align:left;padding:9px 8px;color:#D8DCE0;}}QPushButton:checked{{color:white;border-left:3px solid {ACCENT};background:#6A20C8;}}")
            button.setChecked(index==0); self.group.addButton(button); self.category_buttons[category]=button
            button.clicked.connect(lambda checked=False,name=category:self.category_selected.emit(name)); rl.addWidget(button,1)
            label=QLabel(str(count)); label.setFixedWidth(32); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setStyleSheet("color:#C8CDD2;background:#0A1016;border:1px solid #1C2730;border-radius:4px;padding:2px;"); rl.addWidget(label); layout.addWidget(row)
        layout.addStretch(); self.scroll.setWidget(content)

    def select_category(self, category: str, emit_signal: bool=False) -> None:
        button=self.category_buttons.get(category.upper())
        if button is None:return
        button.setChecked(True)
        if emit_signal:self.category_selected.emit(category.upper())
