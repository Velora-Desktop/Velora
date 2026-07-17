from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QPushButton

from app.ui.navigation.v_menu import VMenu
from app.core.icon_registry import IconRegistry


class TopBar(QFrame):
    placeholder_requested = Signal()
    back_requested = Signal()
    forward_requested = Signal()
    profile_requested = Signal()
    section_requested = Signal(str)
    search_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(70)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        logo = QPushButton("V")
        logo.setObjectName("veloraLogo")
        logo.setFixedSize(58, 52)
        logo.setStyleSheet("font-family: Georgia; font-size: 30pt; font-weight: 700; padding:0;")
        logo_glow = QGraphicsDropShadowEffect(logo)
        logo_glow.setBlurRadius(16)
        logo_glow.setOffset(0, 0)
        logo_glow.setColor(QColor(175, 104, 255, 145))
        logo.setGraphicsEffect(logo_glow)
        self.menu = VMenu(self)
        logo.clicked.connect(lambda: self.menu.popup(logo.mapToGlobal(logo.rect().bottomLeft())))
        layout.addWidget(logo)

        history_buttons = []
        for icon_id, tooltip in (("back", "Назад"), ("forward", "Вперёд")):
            button = QPushButton()
            button.setIcon(IconRegistry.icon(icon_id))
            button.setIconSize(QSize(18, 18))
            button.setToolTip(tooltip)
            button.setEnabled(False)
            button.setStyleSheet("font-family:'Segoe UI Symbol'; font-size:16pt;")
            layout.addWidget(button)
            history_buttons.append(button)
        self.back_button, self.forward_button = history_buttons
        self.back_button.clicked.connect(self.back_requested)
        self.forward_button.clicked.connect(self.forward_requested)

        self.section_buttons = []
        self._space_glows = {}
        for index, text in enumerate(("ИГРЫ", "ФИЛЬМЫ", "СЕРИАЛЫ", "ПРОГРАММЫ")):
            button = QPushButton(text)
            button.setFixedHeight(50)
            button.setMinimumWidth(98)
            button.setStyleSheet("font-family:'Segoe UI'; font-size:12pt; letter-spacing:0.4px; padding:8px 12px;")
            button.setProperty("active", index == 0)
            tab_glow = QGraphicsDropShadowEffect(button)
            tab_glow.setBlurRadius(18)
            tab_glow.setOffset(0, 3)
            tab_glow.setColor(QColor(143, 54, 255, 120))
            tab_glow.setEnabled(index == 0)
            button.setGraphicsEffect(tab_glow)
            self._space_glows[button] = tab_glow
            button.clicked.connect(lambda checked=False, name=text: self.section_requested.emit(name))
            layout.addWidget(button)
            self.section_buttons.append(button)

        for action in ("search", "add"):
            button = QPushButton()
            button.setIcon(IconRegistry.icon(action))
            button.setIconSize(QSize(19, 19))
            button.setToolTip("Глобальный поиск" if action == "search" else "Создать раздел")
            if action == "search":
                self.search_button = button
                button.clicked.connect(self.search_requested)
            else:
                button.clicked.connect(self.placeholder_requested)
            button.setFixedSize(44, 40)
            button.setStyleSheet("border:1px solid #27313A; border-radius:7px; background:#070B10;" if action == "add" else "")
            layout.addWidget(button)

        layout.addStretch(1)
        self.profile_button = QPushButton("МОЙ VELORA")
        self.profile_button.setMinimumWidth(210)
        self.profile_button.setStyleSheet("font-family: Georgia; font-size:18pt; letter-spacing:1.5px; padding:8px 14px;")
        profile_glow = QGraphicsDropShadowEffect(self.profile_button)
        profile_glow.setBlurRadius(12)
        profile_glow.setOffset(0, 0)
        profile_glow.setColor(QColor(143, 54, 255, 120))
        profile_glow.setEnabled(False)
        self.profile_button.setGraphicsEffect(profile_glow)
        self._space_glows[self.profile_button] = profile_glow
        self.profile_button.clicked.connect(self.profile_requested)
        layout.addWidget(self.profile_button)

    def set_profile_active(self, active: bool) -> None:
        self.profile_button.setProperty("active", active)
        if active:
            for button in self.section_buttons:
                button.setProperty("active", False)
                button.style().unpolish(button); button.style().polish(button)
        self.profile_button.style().unpolish(self.profile_button); self.profile_button.style().polish(self.profile_button)
        self._refresh_space_glows()

    def set_search_active(self, active: bool) -> None:
        self.search_button.setProperty("active", active)
        self.search_button.setStyleSheet(
            "border-bottom:2px solid #8B2CF5; background:#120B1D;" if active else ""
        )

    def set_active_space(self, name: str) -> None:
        self.profile_button.setProperty("active", name == "МОЙ VELORA")
        for button in self.section_buttons:
            button.setProperty("active", button.text() == name)
            button.style().unpolish(button); button.style().polish(button)
        self.profile_button.style().unpolish(self.profile_button); self.profile_button.style().polish(self.profile_button)
        self._refresh_space_glows()

    def _refresh_space_glows(self) -> None:
        for button, effect in self._space_glows.items():
            effect.setEnabled(bool(button.property("active")))
