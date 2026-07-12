from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QSizePolicy

from app.ui.navigation.v_menu import VMenu


class TopBar(QFrame):
    placeholder_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(72)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        logo = QPushButton("V")
        logo.setFixedSize(48, 48)
        logo.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.menu = VMenu(self)
        self.menu.placeholder_requested.connect(self.placeholder_requested)
        logo.clicked.connect(lambda: self.menu.popup(logo.mapToGlobal(logo.rect().bottomLeft())))
        layout.addWidget(logo)

        for text in ("←", "→"):
            button = QPushButton(text)
            button.setEnabled(False)
            layout.addWidget(button)

        for index, text in enumerate(("ИГРЫ", "ФИЛЬМЫ", "СЕРИАЛЫ")):
            button = QPushButton(text)
            button.setProperty("active", index == 0)
            if index:
                button.clicked.connect(self.placeholder_requested)
            layout.addWidget(button)

        for text in ("⌕", "+"):
            button = QPushButton(text)
            button.setToolTip("Глобальный поиск" if text == "⌕" else "Создать раздел")
            button.clicked.connect(self.placeholder_requested)
            layout.addWidget(button)

        spacer = QFrame()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(spacer)
        profile = QPushButton("МОЙ VELORA")
        profile.clicked.connect(self.placeholder_requested)
        layout.addWidget(profile)

