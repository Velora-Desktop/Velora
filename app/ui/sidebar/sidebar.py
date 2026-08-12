from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from app.core.constants import ACCENT
from app.core.icon_registry import IconRegistry
from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.components import HoverAnimatedIcon
from app.styles.theme import SURFACE_PANEL


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

SEMANTIC_CATEGORY_ICONS = {
    "RPG": "genre.rpg",
    "БОЕВИК": "genre.action",
    "ЭКШЕН": "genre.action",
    "ЭКШН": "genre.action",
    "ГОНКИ": "genre.racing",
    "СТРАТЕГИИ": "genre.strategy",
    "ПРИКЛЮЧЕНИЯ": "genre.adventure",
    "ФАЙТИНГИ": "genre.fighting",
    "ДРАМА": "genre.drama",
    "КОМЕДИЯ": "genre.comedy",
    "ФЭНТЕЗИ": "genre.fantasy",
    "СИСТЕМНЫЕ": "genre.system",
    "ГРАФИКА": "genre.graphics",
}

ANIMATED_CATEGORY_ICONS = {
    "КОМЕДИЯ": "animated.genre_comedy",
    "АНИМАЦИЯ": "animated.genre_animation",
}


class CategoryButton(QPushButton):
    """Keep long category names readable without pushing out the counter."""
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent); self.full_text = text
        self._animated_icon = None

    def set_animated_icon(self, key: str) -> None:
        self.setIcon(QIcon())
        self.setProperty("animatedIcon", True)
        self._animated_icon = HoverAnimatedIcon(
            key, 18, self, frame_interval_ms=41, mouse_transparent=True,
        )
        self._animated_icon.setObjectName(
            "animatedComedyCategoryIcon"
            if key == "animated.genre_comedy"
            else "animatedAnimationCategoryIcon"
        )
        self._animated_icon.attach_hover_source(self)
        self._position_animated_icon()

    def _position_animated_icon(self) -> None:
        if self._animated_icon is not None:
            self._animated_icon.move(10, max(0, (self.height() - 18) // 2))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_animated_icon()
        available = max(40, self.width() - 42)
        self.setText(self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideRight, available))


class Sidebar(QFrame):
    placeholder_requested = Signal()
    category_selected = Signal(str)
    subcategory_requested = Signal()
    item_requested = Signal()

    def __init__(self, category_counts: dict[str, int] | None = None, parent=None) -> None:
        super().__init__(parent); self.setObjectName("panel"); self.setMinimumWidth(220); self.setMaximumWidth(290)
        self.root = QVBoxLayout(self); self.root.setContentsMargins(10,14,10,10)
        self.scroll = QScrollArea(); self.scroll.setObjectName("sidebarScroll"); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            f"QScrollArea#sidebarScroll{{background:{SURFACE_PANEL};border:0;}}"
        )
        self.scroll.viewport().setStyleSheet(
            f"background:{SURFACE_PANEL};border:0;"
        )
        self.root.addWidget(self.scroll,1)
        self.add_category = QPushButton("＋  ПОДКАТЕГОРИЯ")
        self.add_item = QPushButton("＋  СВОЙ ОБЪЕКТ")
        self.add_category.setMinimumHeight(44); self.add_item.setMinimumHeight(44)
        self.add_category.setToolTip("Добавить категорию и подкатегорию")
        self.add_category.setStyleSheet(
            f"color:#B56CFF;border:1px solid {ACCENT};text-align:left;"
            "font-size:9pt;padding:6px 8px;"
        )
        self.add_item.setStyleSheet(
            "border:1px solid #28343D;text-align:left;font-size:9pt;padding:6px 8px;"
        )
        self.add_category.clicked.connect(self.subcategory_requested)
        self.add_item.clicked.connect(self.item_requested)
        self.root.addWidget(self.add_category); self.root.addWidget(self.add_item)
        self.category_buttons: dict[str,QPushButton] = {}; self.set_categories(category_counts or {})

    def set_categories(self, category_counts: dict[str, int]) -> None:
        content=QWidget(); content.setObjectName("sidebarCategories"); content.setStyleSheet(f"QWidget#sidebarCategories{{background:{SURFACE_PANEL};}}")
        layout=QVBoxLayout(content); layout.setContentsMargins(0,8,0,8)
        self.group=QButtonGroup(self); self.group.setExclusive(True); self.category_buttons={}
        for index,(category,count) in enumerate(category_counts.items()):
            row=QFrame(); row.setObjectName("sidebarCategoryRow"); row.setStyleSheet("QFrame#sidebarCategoryRow{background:transparent;border:0;}"); row.setMinimumWidth(220); rl=QHBoxLayout(row); rl.setContentsMargins(0,0,4,0); rl.setSpacing(6)
            button=CategoryButton(category)
            semantic_key = SEMANTIC_CATEGORY_ICONS.get(category.upper())
            animated_key = ANIMATED_CATEGORY_ICONS.get(category.upper())
            if animated_key:
                button.set_animated_icon(animated_key)
            elif semantic_key:
                button.setIcon(IconProvider.icon(semantic_key, 18, "#D8DCE0"))
            else:
                icon_name, icon_category, variant = ICON_BY_CATEGORY.get(category,("folder_tree","ui","svg"))
                button.setIcon(IconRegistry.icon(icon_name, variant=variant, category=icon_category))
            button.setIconSize(QSize(18,18)); button.setCheckable(True); button.setProperty("category",True)
            button.setMinimumWidth(0); button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); button.setToolTip(category.title())
            button.setStyleSheet(
                "QPushButton{font-size:10pt;text-align:left;padding:9px 8px;"
                "color:#D8DCE0;background:transparent;border:0;"
                "padding-left:11px;}"
                "QPushButton[animatedIcon=\"true\"]{padding-left:35px;}"
                "QPushButton:hover{color:#E7D5F7;background:#35164F;}"
                "QPushButton:checked{color:white;background:#6A20C8;}"
                "QPushButton:checked:hover{color:white;background:#6A20C8;}"
            )
            button.setChecked(index==0); self.group.addButton(button); self.category_buttons[category]=button
            button.clicked.connect(lambda checked=False,name=category:self.category_selected.emit(name)); rl.addWidget(button,1)
            label=QLabel(str(count)); label.setFixedSize(38,34); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Fixed); label.setStyleSheet("color:#C8CDD2;background:#0A1016;border:1px solid #1C2730;border-radius:5px;padding:2px;"); rl.addWidget(label,0,Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); layout.addWidget(row)
        layout.addStretch(); self.scroll.setWidget(content)

    def select_category(self, category: str, emit_signal: bool=False) -> None:
        button=self.category_buttons.get(category.upper())
        if button is None:return
        button.setChecked(True)
        if emit_signal:self.category_selected.emit(category.upper())
