from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from app.core.constants import ACCENT


@dataclass(frozen=True)
class GameData:
    title: str
    general_score: str
    personal_score: str
    status: str
    developer: str
    year: str
    platform: str
    mode: str
    playtime: str = "—"
    description: str = "Краткая информация об игре появится здесь."


class GameRow(QFrame):
    selected = Signal(object)
    placeholder_requested = Signal()

    def __init__(self, game: GameData, parent=None) -> None:
        super().__init__(parent)
        self.game = game
        self._selected = False
        self.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
        self._apply_style()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self.star = QPushButton("☆")
        self.star.setFixedWidth(34)
        self.star.clicked.connect(self._toggle_star)
        layout.addWidget(self.star)
        cover = QLabel("▧")
        cover.setFixedSize(38, 48)
        cover.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        cover.setStyleSheet("background:#292C35; border-radius:4px;")
        layout.addWidget(cover)
        title = QLabel(game.title)
        title.setMinimumWidth(180)
        layout.addWidget(title, 2)
        for text, width in ((game.general_score, 58), (game.personal_score, 58), (game.status, 105),
                            (game.developer, 150), (game.year, 55), (game.platform, 65), (game.mode, 105)):
            label = QLabel(text)
            label.setMinimumWidth(width)
            layout.addWidget(label)
        more = QPushButton("•••")
        more.setFixedWidth(45)
        more.clicked.connect(self.placeholder_requested)
        layout.addWidget(more)

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self.game)
        super().mousePressEvent(event)

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._apply_style()

    def _apply_style(self) -> None:
        border = f"1px solid {ACCENT}" if self._selected else "1px solid #292C35"
        self.setStyleSheet(f"GameRow {{ background:#17191F; border:{border}; border-radius:7px; }} GameRow:hover {{ background:#1D2028; }}")

    def _toggle_star(self) -> None:
        self.star.setText("★" if self.star.text() == "☆" else "☆")
        self.star.setStyleSheet(f"color:{ACCENT};" if self.star.text() == "★" else "")

