from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QPushButton

from app.ui.navigation.v_menu import VMenu


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
        for text in ("←", "→"):
            button = QPushButton(text)
            button.setEnabled(False)
            button.setStyleSheet("font-family:'Segoe UI Symbol'; font-size:16pt;")
            layout.addWidget(button)
            history_buttons.append(button)
        self.back_button, self.forward_button = history_buttons
        self.back_button.clicked.connect(self.back_requested)
        self.forward_button.clicked.connect(self.forward_requested)

        self.section_buttons = []
        for index, text in enumerate(("ИГРЫ", "ФИЛЬМЫ", "СЕРИАЛЫ", "ПРОГРАММЫ")):
            button = QPushButton(text)
            button.setFixedHeight(50)
            button.setMinimumWidth(118)
            button.setStyleSheet("font-family:'Segoe UI'; font-size:13pt; letter-spacing:0.5px; padding:8px 16px;")
            button.setProperty("active", index == 0)
            if index == 0:
                tab_glow = QGraphicsDropShadowEffect(button)
                tab_glow.setBlurRadius(18)
                tab_glow.setOffset(0, 3)
                tab_glow.setColor(QColor(143, 54, 255, 120))
                button.setGraphicsEffect(tab_glow)
            button.clicked.connect(lambda checked=False, name=text: self.section_requested.emit(name))
            layout.addWidget(button)
            self.section_buttons.append(button)

        for text in ("⌕", "+"):
            button = QPushButton(text)
            button.setToolTip("Глобальный поиск" if text == "⌕" else "Создать раздел")
            if text == "⌕":
                self.search_button = button
                button.clicked.connect(self.search_requested)
            else:
                button.clicked.connect(self.placeholder_requested)
            button.setFixedSize(44, 40)
            if text == "+":
                button.setStyleSheet("font-family:'Segoe UI'; font-size:18pt; border:1px solid #27313A; border-radius:7px; background:#070B10;")
            else:
                button.setStyleSheet("font-family:'Segoe UI Symbol'; font-size:17pt;")
            layout.addWidget(button)

        layout.addStretch(1)
        self.profile_button = QPushButton("МОЙ VELORA")
        self.profile_button.setStyleSheet("font-family: Georgia; font-size:20pt; letter-spacing:2px; padding:8px 18px;")
        profile_glow = QGraphicsDropShadowEffect(self.profile_button)
        profile_glow.setBlurRadius(12)
        profile_glow.setOffset(0, 0)
        profile_glow.setColor(QColor(255, 255, 255, 70))
        self.profile_button.setGraphicsEffect(profile_glow)
        self.profile_button.clicked.connect(self.profile_requested)
        layout.addWidget(self.profile_button)

    def set_profile_active(self, active: bool) -> None:
        self.profile_button.setProperty("active", active)
        if active:
            for button in self.section_buttons:
                button.setProperty("active", False)
                button.style().unpolish(button); button.style().polish(button)
        self.profile_button.style().unpolish(self.profile_button); self.profile_button.style().polish(self.profile_button)

    def set_search_active(self, active: bool) -> None:
        self.search_button.setProperty("active", active)
        self.search_button.setStyleSheet(
            "font-family:'Segoe UI Symbol'; font-size:17pt; "
            + ("color:#C286FF; border-bottom:2px solid #8B2CF5;" if active else "")
        )

    def set_active_space(self, name: str) -> None:
        self.profile_button.setProperty("active", name == "МОЙ VELORA")
        for button in self.section_buttons:
            button.setProperty("active", button.text() == name)
            button.style().unpolish(button); button.style().polish(button)
        self.profile_button.style().unpolish(self.profile_button); self.profile_button.style().polish(self.profile_button)
