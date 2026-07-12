from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.ui.catalog.game_row import GameData


class QuickView(QFrame):
    placeholder_requested = Signal()
    closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("quickView")
        self.setMinimumHeight(190)
        self.setMaximumHeight(300)
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 14, 14, 14)
        self.cover = QLabel("▧")
        self.cover.setFixedSize(110, 150)
        self.cover.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#292C35; border-radius:6px; font-size:30px;")
        root.addWidget(self.cover)
        info = QVBoxLayout()
        self.title = QLabel()
        self.title.setStyleSheet("font-size:22px; font-weight:650;")
        info.addWidget(self.title)
        self.meta = QLabel()
        self.meta.setObjectName("muted")
        info.addWidget(self.meta)
        self.description = QLabel()
        self.description.setWordWrap(True)
        info.addWidget(self.description)
        actions = QHBoxLayout()
        for text in ("Открыть страницу", "Изменить оценку"):
            button = QPushButton(text)
            button.clicked.connect(self.placeholder_requested)
            actions.addWidget(button)
        actions.addStretch()
        info.addLayout(actions)
        root.addLayout(info, 1)
        close = QPushButton("×")
        close.setFixedSize(36, 36)
        close.clicked.connect(self._close)
        root.addWidget(close, 0)

    def set_game(self, game: GameData) -> None:
        self.title.setText(game.title)
        self.meta.setText(
            f"Общая: {game.general_score}     Моя: {game.personal_score}     "
            f"{game.status}     Время: {game.playtime}"
        )
        self.description.setText(game.description)
        self.show()

    def _close(self) -> None:
        self.hide()
        self.closed.emit()

