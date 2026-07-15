from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from app.core.constants import ACCENT, DANGER, SUCCESS, WARNING
from app.models.game import GameData
from app.core.icon_registry import IconRegistry
from app.ui.widgets.platform_icons import PlatformIconRow
from app.ui.widgets.age_rating import AgeRatingValue


COLUMN_WIDTHS = {
    "general": 130,
    "personal": 120,
    "status": 180,
    "developer": 170,
    "year": 105,
    "platform": 155,
    "mode": 165,
    "age": 105,
    "more": 45,
}
COLUMN_SPACING = 8
COLUMN_KEYS = ("general", "personal", "status", "developer", "year", "platform", "mode", "age", "more")
COLUMN_AREA_WIDTH = sum(COLUMN_WIDTHS[key] for key in COLUMN_KEYS) + COLUMN_SPACING * (len(COLUMN_KEYS) - 1)
COLUMN_LABELS = {
    "general": "Общая оценка", "personal": "Моя оценка", "status": "Статус",
    "developer": "Разработчик", "year": "Год выхода", "platform": "Платформа",
    "mode": "Кол-во игроков", "age": "Возраст",
}


class GameRow(QFrame):
    selected = Signal(object)
    placeholder_requested = Signal()
    status_changed = Signal(object, str)
    favorite_changed = Signal(object, bool)
    rating_requested = Signal(object)
    detail_requested = Signal(object)
    hidden_requested = Signal(object)

    def __init__(self, game: GameData, parent=None) -> None:
        super().__init__(parent)
        self.game = game
        self._selected = False
        self.column_widgets: dict[str, QWidget] = {}
        self.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
        self._apply_style()
        layout = QHBoxLayout(self)
        self.setFixedHeight(49)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(COLUMN_SPACING)

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
        title.setMinimumWidth(170)
        title.setStyleSheet("font-family:'Segoe UI'; font-size:10.5pt; font-weight:500;")
        layout.addWidget(title, 2)

        columns = QWidget()
        columns.setObjectName("rowColumns")
        columns.setStyleSheet("QWidget#rowColumns { background:transparent; }")
        columns.setFixedWidth(COLUMN_AREA_WIDTH)
        columns_layout = QHBoxLayout(columns)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(COLUMN_SPACING)
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
                self.status_button.setMenu(build_status_menu(self.status_button, self.set_status, game.media_type))
                columns_layout.addWidget(self.status_button)
                self.column_widgets["status"] = self.status_button
                continue
            if column == 5:
                platforms = PlatformIconRow(text, colored=False, centered=True)
                platforms.setFixedWidth(width)
                platforms.setToolTip(text)
                columns_layout.addWidget(platforms)
                self.column_widgets["platform"] = platforms
                continue
            if column == 7:
                age = AgeRatingValue(game.age_rating, centered=True); age.setFixedWidth(width)
                columns_layout.addWidget(age)
                self.column_widgets["age"] = age
                continue
            label = QPushButton(display_text) if column == 1 else QLabel(display_text)
            label.setFixedWidth(width)
            if isinstance(label, QLabel):
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if column in (0, 1):
                if column == 0:
                    label.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet(f"font-family:'Segoe UI'; font-size:12pt; font-weight:600; color:{self._score_color(text)};")
                if column == 0:
                    self.general_score_label = label
                else:
                    self.personal_score_label = label
                    label.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
                    label.setToolTip("Поставить или изменить личную оценку")
                    label.clicked.connect(lambda checked=False: self.rating_requested.emit(self.game))
            columns_layout.addWidget(label)
            self.column_widgets[COLUMN_KEYS[column]] = label
        more = QPushButton("•••")
        more.setFixedWidth(COLUMN_WIDTHS["more"])
        menu = QMenu(more)
        open_action = menu.addAction("Открыть страницу")
        open_action.triggered.connect(lambda: self.detail_requested.emit(self.game))
        favorite_action = menu.addAction("Добавить/убрать из избранного")
        favorite_action.triggered.connect(self._toggle_star)
        hide_action = menu.addAction("Скрыть у меня")
        hide_action.triggered.connect(lambda: self.hidden_requested.emit(self.game))
        more.setMenu(menu)
        columns_layout.addWidget(more)
        self.column_widgets["more"] = more
        layout.addWidget(columns)

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self.game)
        super().mousePressEvent(event)

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._apply_style()

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                f"GameRow {{ background:#160B24; border:1px solid {ACCENT}; border-radius:7px; }} "
                "GameRow QWidget#rowColumns { background:transparent; } "
                "GameRow QLabel { background:transparent; }"
            )
        else:
            self.setStyleSheet(
                "GameRow { background:transparent; border:0; border-bottom:1px solid #24272B; border-radius:0; } "
                "GameRow:hover { background:#160B24; } "
                "GameRow QWidget#rowColumns { background:transparent; } "
                "GameRow QLabel { background:transparent; }"
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
        from app.ui.catalog.status_menu import status_visual
        color, border_color, background = status_visual(status)
        border = f"1px solid {border_color}" if background != "transparent" else "0"
        return (
            f"QPushButton {{ color:{color}; border:{border}; border-radius:5px; "
            f"padding:3px 22px 3px 8px; background:{background}; text-align:center; }}"
            "QPushButton::menu-indicator { subcontrol-position:right center; right:8px; }"
        )
