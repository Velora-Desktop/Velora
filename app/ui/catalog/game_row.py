from datetime import datetime

from PySide6.QtCore import QSize, Signal
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from app.core.constants import ACCENT, DANGER, SUCCESS, WARNING
from app.core.paths import resolve_resource_path
from app.models.game import GameData
from app.core.icon_registry import IconRegistry
from app.ui.widgets.platform_icons import PlatformIconRow
from app.ui.widgets.age_rating import AgeRatingValue
from app.ui.widgets.clickable_label import ClickableLabel
from app.ui.widgets.company_logo_row import CompanyLogoRow
from app.ui.catalog.status_menu import StatusButton
from app.core.display_text import compact_entities
from app.ui.rating_palette import rating_color
from app.ui.velora_ui.motion import animate_icon_pulse, apply_favorite_icon


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
    aw02_action_requested = Signal(object, str)

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

        self.star = QPushButton()
        self.star.setFixedSize(36, 36)
        self.star.setStyleSheet(
            "QPushButton { padding:0; margin:0; border:0; background:transparent; }"
            "QPushButton:hover { background:#17212B; border-radius:5px; }"
        )
        self.star.setIconSize(QSize(20, 20))
        self._favorite_animation = None
        apply_favorite_icon(self.star, self.game.favorite, size=20)
        self.star.clicked.connect(self._toggle_star)
        layout.addWidget(self.star)
        self.cover = QLabel("")
        self.cover.setFixedSize(28, 42)
        self.cover.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#18212A; border:0; border-radius:2px;")
        cover_path = resolve_resource_path(game.cover_path) if game.cover_path else None
        if cover_path and cover_path.is_file():
            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                self.cover.setPixmap(pixmap.scaled(
                    self.cover.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
        layout.addWidget(self.cover)
        self.title_button = ClickableLabel(game.title)
        self.title_button.setObjectName("catalogTitleLink")
        self.title_button.setMinimumWidth(170)
        self.title_button.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.title_button.setToolTip("Показать быстрый просмотр")
        self.title_button.setStyleSheet(
            "QLabel#catalogTitleLink {"
            "font-family:'Segoe UI';font-size:10.5pt;font-weight:500;"
            "text-align:left;padding:0 6px;border:0;background:transparent;color:#F1F2F4;"
            "}"
            "QLabel#catalogTitleLink:hover {color:#CFA1FF;background:transparent;}"
            "QLabel#catalogTitleLink:focus {color:#CFA1FF;background:transparent;}"
        )
        self.title_button.clicked.connect(
            lambda checked=False: self.selected.emit(self.game)
        )
        layout.addWidget(self.title_button, 2)

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
            full_tooltip = ""
            if column == 3:
                display_text, full_tooltip = compact_entities(text)
            if column == 2:
                self.status_button = StatusButton(self.set_status, game.media_type)
                self.status_button.setFixedWidth(width)
                self.status_button.setMinimumHeight(34)
                self.status_button.set_status(text)
                columns_layout.addWidget(self.status_button)
                self.column_widgets["status"] = self.status_button
                continue
            if column == 5:
                platforms = PlatformIconRow(text, colored=False, centered=True)
                platforms.setFixedWidth(width)
                columns_layout.addWidget(platforms)
                self.column_widgets["platform"] = platforms
                continue
            if column == 3:
                companies = CompanyLogoRow(max_visible=1, compact=True)
                companies.setFixedWidth(width)
                companies.setText(text)
                companies.setToolTip(full_tooltip)
                columns_layout.addWidget(companies)
                self.column_widgets["developer"] = companies
                continue
            if column == 7:
                age = AgeRatingValue(game.age_rating, centered=True); age.setFixedWidth(width)
                columns_layout.addWidget(age)
                self.column_widgets["age"] = age
                continue
            label = QPushButton(display_text) if column == 1 else QLabel(display_text)
            label.setFixedWidth(width)
            if full_tooltip:
                label.setToolTip(full_tooltip)
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
        self.more_button = more
        more.setObjectName("catalogRowMoreButton")
        more.setFixedSize(COLUMN_WIDTHS["more"], 34)
        more.setCursor(Qt.CursorShape.PointingHandCursor)
        more.setStyleSheet(
            "QPushButton#catalogRowMoreButton{background:transparent;border:0;"
            "border-radius:0;color:#EEF1F4;font-family:'Segoe UI';"
            "font-size:12pt;font-weight:700;padding:0;}"
            f"QPushButton#catalogRowMoreButton:hover{{background:transparent;"
            f"border:0;color:{ACCENT};}}"
            f"QPushButton#catalogRowMoreButton:pressed{{background:transparent;"
            f"color:#CFA1FF;}}"
            "QPushButton#catalogRowMoreButton:focus{outline:none;"
            "background:transparent;border:0;}"
            "QPushButton#catalogRowMoreButton::menu-indicator{"
            "image:none;width:0;height:0;}"
        )
        menu = QMenu(more)
        favorite_action = menu.addAction("Добавить/убрать из избранного")
        favorite_action.triggered.connect(self._toggle_star)
        hide_action = menu.addAction("Скрыть у меня")
        hide_action.triggered.connect(lambda: self.hidden_requested.emit(self.game))
        more.setMenu(menu)
        columns_layout.addWidget(more)
        self.column_widgets["more"] = more
        layout.addWidget(columns)
        self.sync_interactive_surfaces()

    def set_aw02_actions(self, actions) -> None:
        from app.application.game_row_contracts import GameRowAction
        # Journey is managed from the game page.  The compact row menu remains
        # a card-level quick-access surface and must not duplicate that flow.
        journey_actions = {
            GameRowAction.START_PLAYTHROUGH,
            GameRowAction.CONTINUE_PLAYTHROUGH,
            GameRowAction.ADD_PLAYTIME,
            GameRowAction.ADD_CHECKPOINT,
            GameRowAction.ADD_IMPRESSION,
            GameRowAction.RATE,
            GameRowAction.COMPLETE_PLAYTHROUGH,
        }
        menu = QMenu(self.more_button)
        for action in actions:
            if action is GameRowAction.OPEN or action in journey_actions:
                continue
            item = menu.addAction(action.value)
            item.triggered.connect(
                lambda checked=False, value=action:
                self.aw02_action_requested.emit(self.game, value.value)
            )
        favorite = menu.addAction("Добавить/убрать из избранного")
        favorite.triggered.connect(self._toggle_star)
        hide = menu.addAction("Скрыть у меня")
        hide.triggered.connect(lambda: self.hidden_requested.emit(self.game))
        self.more_button.setMenu(menu)

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self.game)
        super().mousePressEvent(event)

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self._apply_style()
        self.sync_interactive_surfaces()

    def sync_interactive_surfaces(self) -> None:
        """Keep child controls transparent; the row owns the hover surface."""
        score = getattr(self, "personal_score_label", None)
        if score is not None:
            color = self._score_color(self.game.personal_score)
            style = (
                "QPushButton {"
                "font-family:'Segoe UI';font-size:12pt;font-weight:600;"
                f"color:{color};background:transparent;border:0;"
                "border-radius:0;padding:0;}"
                "QPushButton:hover {color:#CFA1FF;background:transparent;}"
            )
            if score.styleSheet() != style:
                score.setStyleSheet(style)

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
        if self._favorite_animation is not None:
            self._favorite_animation.stop()
        selected = self.game.favorite
        self._favorite_animation = animate_icon_pulse(
            self.star,
            adding=selected,
            state_change=lambda: apply_favorite_icon(self.star, selected, size=20),
        )
        self.favorite_changed.emit(self.game, self.game.favorite)

    def set_status(self, status: str, record_history: bool = True) -> None:
        self.game.status = status
        self.status_button.set_status(status)
        if record_history:
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
            self.game.history.append(f"{timestamp} — статус: {status}")
        self.status_changed.emit(self.game, status)

    def set_personal_score(self, score: str) -> None:
        self.game.personal_score = score
        self.personal_score_label.setText(self._format_score(score))
        self.sync_interactive_surfaces()

    def sync_from_game(self) -> None:
        self.set_personal_score(self.game.personal_score)
        self.set_status(self.game.status, record_history=False)
        apply_favorite_icon(self.star, self.game.favorite, size=20)

    @staticmethod
    def _score_color(value: str) -> str:
        return rating_color(value)

    @staticmethod
    def _format_score(value: str) -> str:
        if value == "—":
            return value
        return value if "." in value else f"{value}.0"
