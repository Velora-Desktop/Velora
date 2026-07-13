from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from app.core.constants import ACCENT, DANGER, SUCCESS, WARNING


COLUMN_WIDTHS = {
    "general": 150,
    "personal": 135,
    "status": 175,
    "developer": 160,
    "year": 120,
    "platform": 145,
    "mode": 170,
    "age": 90,
    "more": 45,
}


GAME_STATUSES = ("НЕ НАЧИНАЛ", "ПРОХОЖУ", "ПРОШЁЛ", "БРОСИЛ")


@dataclass
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
    publisher: str = "—"
    release_year: str = "—"
    history: list[str] = field(default_factory=list)
    rating_criteria: dict[str, int] = field(default_factory=dict)
    favorite: bool = False
    age_rating: int = 0
    catalog_id: str = ""
    category: str = "Шутеры"
    subgroup: str = ""
    cover_path: str = ""
    critic_scores: dict[str, float | None] = field(default_factory=dict)
    media_type: str = "Игры"
    hidden: bool = False


class GameRow(QFrame):
    selected = Signal(object)
    placeholder_requested = Signal()
    status_changed = Signal(object, str)
    favorite_changed = Signal(object, bool)

    def __init__(self, game: GameData, parent=None) -> None:
        super().__init__(parent)
        self.game = game
        self._selected = False
        self.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
        self._apply_style()
        layout = QHBoxLayout(self)
        self.setFixedHeight(49)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.star = QPushButton("☆")
        self.star.setFixedSize(36, 36)
        self.star.setStyleSheet(
            "QPushButton { font-family:'Segoe UI Symbol'; font-size:15pt; color:#B8C0C8; "
            "padding:0; margin:0; border:0; background:transparent; }"
            "QPushButton:hover { color:white; background:#17212B; border-radius:5px; }"
        )
        self.star.clicked.connect(self._toggle_star)
        layout.addWidget(self.star)
        cover = QLabel("")
        cover.setFixedSize(44, 40)
        cover.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        cover.setStyleSheet("background:#242B36; border:1px solid #313B47; border-radius:4px;")
        layout.addWidget(cover)
        title = QLabel(game.title)
        title.setMinimumWidth(190)
        title.setStyleSheet("font-family:'Segoe UI'; font-size:10.5pt; font-weight:500;")
        layout.addWidget(title, 2)
        for column, (text, width) in enumerate(((game.general_score, COLUMN_WIDTHS["general"]),
                            (game.personal_score, COLUMN_WIDTHS["personal"]),
                            (game.status, COLUMN_WIDTHS["status"]),
                            (game.developer, COLUMN_WIDTHS["developer"]), (game.year, COLUMN_WIDTHS["year"]),
                            (game.platform, COLUMN_WIDTHS["platform"]), (game.mode, COLUMN_WIDTHS["mode"]),
                            (f"{game.age_rating}+", COLUMN_WIDTHS["age"]))):
            display_text = self._format_score(text) if column in (0, 1) else text
            if column == 2:
                self.status_button = QPushButton(display_text)
                self.status_button.setFixedWidth(width)
                self.status_button.setMinimumHeight(34)
                self.status_button.setStyleSheet(self._status_style(text))
                from app.ui.catalog.status_menu import build_status_menu
                self.status_button.setMenu(build_status_menu(self.status_button, self.set_status))
                layout.addWidget(self.status_button)
                continue
            label = QLabel(display_text)
            label.setFixedWidth(width)
            if column in (0, 1):
                label.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet(f"font-family:'Segoe UI'; font-size:12pt; font-weight:600; color:{self._score_color(text)};")
                if column == 0:
                    self.general_score_label = label
                else:
                    self.personal_score_label = label
            layout.addWidget(label)
        more = QPushButton("•••")
        more.setFixedWidth(COLUMN_WIDTHS["more"])
        more.clicked.connect(self.placeholder_requested)
        layout.addWidget(more)

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self.game)
        super().mousePressEvent(event)

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._apply_style()

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                f"GameRow {{ background:#091018; border:1px solid {ACCENT}; border-radius:7px; }} "
                "GameRow QLabel { background:transparent; }"
            )
        else:
            self.setStyleSheet(
                "GameRow { background:#071016; border:0; border-bottom:1px solid #1B2730; border-radius:0; } "
                "GameRow:hover { background:#0D171E; } GameRow QLabel { background:transparent; }"
            )

    def _toggle_star(self) -> None:
        self.game.favorite = not self.game.favorite
        self.star.setText("★" if self.game.favorite else "☆")
        color = ACCENT if self.game.favorite else "#B8C0C8"
        self.star.setStyleSheet(
            f"QPushButton {{ font-family:'Segoe UI Symbol'; font-size:15pt; color:{color}; "
            "padding:0; margin:0; border:0; background:transparent; }"
            "QPushButton:hover { color:white; background:#17212B; border-radius:5px; }"
        )
        self.favorite_changed.emit(self.game, self.game.favorite)

    def set_status(self, status: str, record_history: bool = True) -> None:
        self.game.status = status
        self.status_button.setText(status)
        self.status_button.setStyleSheet(self._status_style(status))
        if record_history:
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
            self.game.history.append(f"{timestamp} — статус: {status}")
        self.status_changed.emit(self.game, status)

    def set_personal_score(self, score: str) -> None:
        self.game.personal_score = score
        self.personal_score_label.setText(self._format_score(score))
        self.personal_score_label.setStyleSheet(
            f"font-family:'Segoe UI'; font-size:12pt; font-weight:600; color:{self._score_color(score)};"
        )

    def sync_from_game(self) -> None:
        self.set_personal_score(self.game.personal_score)
        self.set_status(self.game.status, record_history=False)
        self.star.setText("★" if self.game.favorite else "☆")

    @staticmethod
    def _score_color(value: str) -> str:
        try:
            score = float(value)
        except ValueError:
            return "#8A929A"
        if score >= 8:
            return SUCCESS
        if score >= 5:
            return WARNING
        return DANGER

    @staticmethod
    def _format_score(value: str) -> str:
        if value == "—":
            return value
        return value if "." in value else f"{value}.0"

    @staticmethod
    def _status_style(status: str) -> str:
        if status == "ПРОХОЖУ":
            color, border, background = WARNING, "1px solid #7D5100", "#251A07"
        elif status == "ПРОШЁЛ":
            color, border, background = SUCCESS, "0", "transparent"
        elif status == "БРОСИЛ":
            color, border, background = DANGER, "0", "transparent"
        else:
            color, border, background = "#88919A", "0", "transparent"
        return (
            f"QPushButton {{ color:{color}; border:{border}; border-radius:5px; "
            f"padding:3px 22px 3px 8px; background:{background}; text-align:center; }}"
            "QPushButton::menu-indicator { subcontrol-position:right center; right:8px; }"
        )
