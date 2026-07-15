from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from app.core.constants import ACCENT
from app.core.icon_registry import IconRegistry


ICON_BY_CATEGORY = {
    "ШУТЕРЫ": ("crosshair", "genres", "svg"), "ПРИКЛЮЧЕНИЯ": ("compass", "genres", "svg"),
    "ГОНКИ": ("race", "genres", "svg"), "RPG": ("helmet", "genres", "svg"),
    "СТРАТЕГИИ": ("strategy", "genres", "svg"), "СПОРТИВНЫЕ": ("sport", "genres", "svg"),
    "ФАЙТИНГИ": ("fist", "genres", "svg"), "УЖАСЫ": ("skull", "genres", "svg"),
    "СИМУЛЯТОРЫ": ("gear", "genres", "svg"), "ПЛАТФОРМЕРЫ": ("platform", "genres", "svg"),
    "ГОЛОВОЛОМКИ": ("puzzle", "genres", "svg"), "MMO": ("globe", "genres", "svg"),
    "ДРАМА": ("video_camera", "media", "svg"), "ФАНТАСТИКА": ("globe", "genres", "svg"),
    "БОЕВИК": ("fist", "genres", "svg"), "КОМЕДИЯ": ("announcement", "marketing", "dark"),
    "АНИМАЦИЯ": ("video_media", "media", "dark"), "ДЕТЕКТИВ": ("crosshair", "genres", "svg"),
    "ФЭНТЕЗИ": ("helmet", "genres", "svg"),
    "ОПЕРАЦИОННЫЕ СИСТЕМЫ": ("windows", "platforms", "dark"),
    "СИСТЕМНЫЕ": ("processor", "hardware", "dark"), "ОФИСНЫЕ": ("code_display", "ui", "svg"),
    "ГРАФИКА": ("ai_chip", "hardware", "dark"), "ВИДЕО": ("video_camera", "media", "svg"),
    "АУДИО": ("media_file", "media", "dark"), "РАЗРАБОТКА": ("python", "brands", "svg"),
    "БЕЗОПАСНОСТЬ": ("warning", "feedback", "dark"), "ИНТЕРНЕТ": ("globe", "ui", "dark"),
}


class CategoryButton(QPushButton):
    """Keep long category names readable without pushing out the counter."""
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent); self.full_text = text

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        available = max(40, self.width() - 42)
        self.setText(self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideRight, available))


class Sidebar(QFrame):
    placeholder_requested = Signal()
    category_selected = Signal(str)

    def __init__(self, category_counts: dict[str, int] | None = None, parent=None) -> None:
        super().__init__(parent); self.setObjectName("panel"); self.setMinimumWidth(220); self.setMaximumWidth(290)
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
        for index,(category,count) in enumerate(category_counts.items()):
            row=QFrame(); row.setMinimumWidth(220); rl=QHBoxLayout(row); rl.setContentsMargins(0,0,4,0); rl.setSpacing(6)
            button=CategoryButton(category); icon_name, icon_category, variant=ICON_BY_CATEGORY.get(category,("folder_tree","ui","svg")); button.setIcon(IconRegistry.icon(icon_name, variant=variant, category=icon_category)); button.setIconSize(QSize(18,18)); button.setCheckable(True); button.setProperty("category",True)
            button.setMinimumWidth(0); button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); button.setToolTip(category.title())
            button.setStyleSheet(f"QPushButton{{font-size:10pt;text-align:left;padding:9px 8px;color:#D8DCE0;}}QPushButton:checked{{color:white;border-left:3px solid {ACCENT};background:#6A20C8;}}")
            button.setChecked(index==0); self.group.addButton(button); self.category_buttons[category]=button
            button.clicked.connect(lambda checked=False,name=category:self.category_selected.emit(name)); rl.addWidget(button,1)
            label=QLabel(str(count)); label.setFixedSize(38,34); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Fixed); label.setStyleSheet("color:#C8CDD2;background:#0A1016;border:1px solid #1C2730;border-radius:5px;padding:2px;"); rl.addWidget(label,0,Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); layout.addWidget(row)
        layout.addStretch(); self.scroll.setWidget(content)

    def select_category(self, category: str, emit_signal: bool=False) -> None:
        button=self.category_buttons.get(category.upper())
        if button is None:return
        button.setChecked(True)
        if emit_signal:self.category_selected.emit(category.upper())
