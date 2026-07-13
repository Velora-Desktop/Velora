from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import ACCENT, DANGER, SUCCESS, WARNING
from app.models.game import GameData
from app.ui.catalog.status_menu import build_status_menu
from app.ui.quick_view.rating_dialog import request_rating
from app.ui.quick_view.playtime_dialog import request_total_playtime
from app.ui.quick_view.series_progress_dialog import request_series_progress


class QuickView(QFrame):
    placeholder_requested = Signal()
    closed = Signal()
    status_changed = Signal(object, str)
    playtime_changed = Signal(object, float)
    rating_changed = Signal(object, str)
    favorite_changed = Signal(object, bool)
    detail_requested = Signal(object)
    hidden_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("quickView")
        self.setMinimumHeight(315)
        self.setMaximumHeight(380)
        self.current_game: GameData | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 4, 8, 8)
        root.setSpacing(14)

        # Cover and primary action.
        cover_column = QVBoxLayout()
        cover_column.setSpacing(6)
        self.cover = QLabel()
        self.cover.setFixedSize(145, 185)
        self.cover.setStyleSheet("background:#242B36; border:1px solid #313B47; border-radius:6px;")
        cover_column.addWidget(self.cover)
        rate_button = QPushButton("ОЦЕНИТЬ")
        rate_button.setFixedHeight(36)
        rate_button.setStyleSheet(
            f"background:#6721BA; border:1px solid {ACCENT}; border-radius:5px; "
            "font-weight:600; color:white; text-align:center; padding:0;"
        )
        rate_button.clicked.connect(self._open_rating_dialog)
        cover_column.addWidget(rate_button)
        root.addLayout(cover_column)

        # Title and catalog metadata.
        info = QVBoxLayout()
        info.setSpacing(7)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_button = QPushButton()
        self.title_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_button.setStyleSheet(
            f"QPushButton {{ font-family:'Segoe UI'; font-size:16pt; font-weight:600; "
            "text-align:left; padding:0; border:0; background:transparent; }}"
            f"QPushButton:hover {{ color:{ACCENT}; }}"
        )
        self.title_button.clicked.connect(self._request_detail)
        title_row.addWidget(self.title_button)
        self.favorite_button = QPushButton("☆")
        self.favorite_button.setToolTip("Добавить в избранное")
        self.favorite_button.setFixedSize(34, 34)
        self.favorite_button.setStyleSheet(
            "QPushButton { font-family:'Segoe UI Symbol'; font-size:16pt; padding:0; border:0; background:transparent; }"
            f"QPushButton:hover {{ color:{ACCENT}; }}"
        )
        self.favorite_button.clicked.connect(self._toggle_favorite)
        title_row.addWidget(self.favorite_button)
        title_row.addStretch()
        info.addLayout(title_row)

        meta = QGridLayout()
        meta.setHorizontalSpacing(28)
        meta.setVerticalSpacing(5)
        self.genre = self._meta_value()
        self.year = self._meta_value()
        self.developer = self._meta_value()
        self.platform = self._meta_value()
        self.publisher = self._meta_value()
        self.mode = self._meta_value()
        self.age = self._meta_value()
        empty_value = self._meta_value()
        pairs = (
            ("Жанр:", self.genre, "Год выхода:", self.year),
            ("Разработчик:", self.developer, "Платформа:", self.platform),
            ("Издатель:", self.publisher, "Кол-во игроков:", self.mode),
            ("Возрастной рейтинг:", self.age, "", empty_value),
        )
        self.meta_captions = []
        for row, (left_title, left_value, right_title, right_value) in enumerate(pairs):
            left_layout, left_caption = self._meta_pair(left_title, left_value)
            right_layout, right_caption = self._meta_pair(right_title, right_value)
            self.meta_captions.extend((left_caption, right_caption))
            meta.addLayout(left_layout, row, 0)
            meta.addLayout(right_layout, row, 1)
        info.addLayout(meta)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setMaximumHeight(62)
        self.summary.setStyleSheet("color:#AEB9C2;font-size:9.5pt;padding-top:4px;")
        info.addWidget(self.summary)
        info.addStretch()
        actions = QPushButton("ДЕЙСТВИЯ")
        actions.setFixedSize(145, 36)
        actions.setStyleSheet("border:1px solid #2A3540; background:#0B131A; text-align:left;")
        actions_menu = QMenu(actions)
        for action_text in ("Открыть страницу", "Скрыть у меня"):
            action = actions_menu.addAction(action_text)
            if action_text == "Открыть страницу":
                action.triggered.connect(self._request_detail)
            else:
                action.triggered.connect(self._request_hide)
        actions.setMenu(actions_menu)
        cover_column.addWidget(actions)
        root.addLayout(info, 3)

        root.addWidget(self._divider())

        # Rating card.
        rating_column = QVBoxLayout()
        rating_title = QLabel("ОЦЕНКИ")
        rating_title.setObjectName("caption")
        rating_column.addWidget(rating_title)
        rating_card = QFrame()
        rating_card.setObjectName("ratingCard")
        rating_card.setStyleSheet(
            "QFrame#ratingCard { background:#091118; border:1px solid #27333D; border-radius:7px; }"
            "QFrame#ratingCard QLabel { background:transparent; border:0; }"
            "QFrame#ratingCard QPushButton { background:transparent; }"
        )
        rating_layout = QHBoxLayout(rating_card)
        rating_layout.setContentsMargins(14, 12, 14, 12)
        rating_layout.setSpacing(12)

        general = QVBoxLayout()
        general.addWidget(self._rating_heading("ОБЩАЯ ОЦЕНКА"))
        self.general_score = QLabel()
        self.general_score.setStyleSheet(f"font-size:25pt; font-weight:600; color:{SUCCESS};")
        general.addWidget(self.general_score)
        self.general_stars = QLabel("☆☆☆☆☆")
        self.general_stars.setStyleSheet(f"font-family:'Segoe UI Symbol'; font-size:19pt; color:{SUCCESS};")
        general.addWidget(self.general_stars)
        self.vote_count = QLabel()
        self.vote_count.setObjectName("muted")
        self.vote_count.setWordWrap(True)
        general.addWidget(self.vote_count)
        general.addStretch()
        rating_layout.addLayout(general, 1)

        rating_layout.addWidget(self._divider())

        personal = QVBoxLayout()
        personal.addWidget(self._rating_heading("МОЯ ОЦЕНКА"))
        personal_top = QHBoxLayout()
        self.personal_score = QLabel()
        self.personal_score.setStyleSheet(f"font-size:25pt; font-weight:600; color:{DANGER};")
        personal_top.addWidget(self.personal_score)
        personal_top.addStretch()
        self.status = QPushButton()
        self.status.setStyleSheet(
            f"color:{WARNING}; border:1px solid #775000; border-radius:5px; "
            "background:#251A07; font-weight:600;"
        )
        self.status.setMenu(build_status_menu(self.status, self._change_status))
        personal_top.addWidget(self.status)
        personal.addLayout(personal_top)
        self.personal_stars = QLabel("☆☆☆☆☆")
        self.personal_stars.setStyleSheet(f"font-family:'Segoe UI Symbol'; font-size:19pt; color:{DANGER};")
        personal.addWidget(self.personal_stars)
        personal.addStretch()
        rating_layout.addLayout(personal, 1)
        rating_column.addWidget(rating_card, 1)
        root.addLayout(rating_column, 2)

        root.addWidget(self._divider())

        # Time and scrollable interaction chronology.
        timeline_column = QVBoxLayout()
        self.timeline_title = QLabel("ВРЕМЯ И ХРОНОЛОГИЯ")
        self.timeline_title.setObjectName("caption")
        timeline_column.addWidget(self.timeline_title)
        activity = QGridLayout()
        activity.setHorizontalSpacing(34)
        added_title = QLabel("ДОБАВЛЕНО")
        added_title.setObjectName("caption")
        self.time_title = QLabel("ВРЕМЯ В ИГРЕ")
        self.time_title.setObjectName("caption")
        activity.addWidget(added_title, 0, 0)
        activity.addWidget(self.time_title, 0, 1)
        self.added = QLabel("12.05.2024")
        self.playtime = QLabel()
        activity.addWidget(self.added, 1, 0)
        activity.addWidget(self.playtime, 1, 1)
        timeline_column.addLayout(activity)
        self.time_button = QPushButton("ИЗМЕНИТЬ ОБЩЕЕ ВРЕМЯ")
        self.time_button.setStyleSheet("border:1px solid #2A3540; background:#0B131A; text-align:left;")
        self.time_button.clicked.connect(self._open_media_progress_dialog)
        timeline_column.addWidget(self.time_button)
        history_title = QLabel("ПОСЛЕДНИЕ ИЗМЕНЕНИЯ")
        history_title.setObjectName("caption")
        timeline_column.addWidget(history_title)
        history_scroll = QScrollArea()
        history_scroll.setWidgetResizable(True)
        history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        history_scroll.setStyleSheet("QScrollArea { border:1px solid #26333D; border-radius:6px; background:#071016; }")
        history_content = QWidget()
        history_layout = QVBoxLayout(history_content)
        history_layout.setContentsMargins(8, 6, 8, 6)
        self.history_label = QLabel("Изменений пока нет")
        self.history_label.setObjectName("muted")
        self.history_label.setWordWrap(True)
        self.history_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        history_layout.addWidget(self.history_label)
        history_layout.addStretch()
        history_scroll.setWidget(history_content)
        timeline_column.addWidget(history_scroll, 1)
        root.addLayout(timeline_column, 2)

        close_column = QVBoxLayout()
        close = QPushButton("×")
        close.setToolTip("Закрыть быстрый просмотр")
        close.setFixedSize(32, 32)
        close.setStyleSheet("font-family:'Segoe UI Symbol'; font-size:17pt; color:#B8C0C8; padding:0;")
        close.clicked.connect(self._close)
        close_column.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        close_column.addStretch()
        root.addLayout(close_column)

    @staticmethod
    def _meta_value() -> QLabel:
        label = QLabel()
        label.setStyleSheet("font-weight:500; color:#E7E9EC;")
        return label

    @staticmethod
    def _meta_pair(title: str, value: QLabel):
        layout = QVBoxLayout()
        layout.setSpacing(1)
        caption = QLabel(title)
        caption.setObjectName("muted")
        layout.addWidget(caption)
        layout.addWidget(value)
        return layout, caption

    @staticmethod
    def _rating_heading(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size:10pt; font-weight:600;")
        return label

    @staticmethod
    def _divider() -> QFrame:
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("color:#26313A;")
        return divider

    @staticmethod
    def _horizontal_divider() -> QFrame:
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color:#26313A;")
        return divider

    def set_game(self, game: GameData) -> None:
        self.status.setMenu(build_status_menu(self.status, self._change_status, game.media_type))
        self.current_game = game
        labels = {
            "Игры": ("Жанр:","Год выхода:","Разработчик:","Платформа:","Издатель:","Кол-во игроков:","Возраст:",""),
            "Фильмы": ("Жанр:","Год выхода:","Режиссёр:","Где смотреть:","Студия:","Длительность:","Возраст:",""),
            "Сериалы": ("Жанр:","Год выхода:","Создатель:","Где смотреть:","Студия:","Сезоны:","Возраст:",""),
            "Программы": ("Категория:","Год выхода:","Разработчик:","Платформа:","Издатель:","Тип:","Возраст:",""),
        }[game.media_type]
        for caption, text in zip(self.meta_captions, labels): caption.setText(text)
        self.title_button.setText(game.title)
        self.genre.setText(" · ".join(part for part in (game.category, game.subgroup) if part))
        self.year.setText(game.year)
        self.developer.setText(game.developer)
        self.platform.setText(game.platform)
        self.publisher.setText(game.publisher)
        self.mode.setText(game.mode)
        self.age.setText(f"{game.age_rating}+")
        summary = game.description.strip()
        self.summary.setText(summary if len(summary) <= 190 else summary[:187].rstrip() + "…")
        self.general_score.setText(self._format_score(game.general_score))
        sources = [name for name, value in game.critic_scores.items() if value is not None]
        self.vote_count.setText("На основе: " + (", ".join(sources) if sources else "источники не указаны"))
        self.personal_score.setText(self._format_score(game.personal_score))
        self.general_stars.setText(self._stars_for_score(game.general_score))
        self.personal_stars.setText(self._stars_for_score(game.personal_score))
        personal_color = self._score_color(game.personal_score)
        self.personal_score.setStyleSheet(f"font-size:25pt; font-weight:600; color:{personal_color};")
        self.personal_stars.setStyleSheet(
            f"font-family:'Segoe UI Symbol'; font-size:19pt; color:{personal_color};"
        )
        self.status.setText(game.status)
        self._configure_media_progress(game)
        self.favorite_button.setText("★" if game.favorite else "☆")
        self._update_status_style(game.status)
        self._refresh_history()
        self.show()

    def set_external_status(self, game: GameData, status: str) -> None:
        if self.current_game is game:
            self.status.setText(status)
            self._update_status_style(status)
            self._refresh_history()

    def _change_status(self, status: str) -> None:
        if self.current_game is None:
            return
        self.current_game.status = status
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.current_game.history.append(f"{timestamp} — статус: {status}")
        self.status.setText(status)
        self._update_status_style(status)
        self._refresh_history()
        self.status_changed.emit(self.current_game, status)

    def _update_status_style(self, status: str) -> None:
        from app.ui.catalog.status_menu import status_visual
        color, border, background = status_visual(status)
        self.status.setStyleSheet(
            f"color:{color}; border:1px solid {border}; border-radius:5px; "
            f"background:{background}; font-weight:600;"
        )

    def _open_rating_dialog(self) -> None:
        if self.current_game is None:
            return
        criteria = request_rating(self.current_game.rating_criteria, self, self.current_game.media_type)
        if criteria is not None: self._record_rating(criteria)

    def _record_rating(self, criteria: dict[str, int]) -> None:
        if self.current_game is None or not criteria:
            return
        score = sum(criteria.values()) / len(criteria)
        score_text = f"{score:.1f}"
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.current_game.rating_criteria = dict(criteria)
        self.current_game.personal_score = score_text
        self.current_game.history.append(f"{timestamp} — оценка: {score_text}")
        self.personal_score.setText(score_text)
        self.personal_stars.setText(self._stars_for_score(score_text))
        color = self._score_color(score_text)
        self.personal_score.setStyleSheet(f"font-size:25pt; font-weight:600; color:{color};")
        self.personal_stars.setStyleSheet(
            f"font-family:'Segoe UI Symbol'; font-size:19pt; color:{color};"
        )
        self._refresh_history()
        self.rating_changed.emit(self.current_game, score_text)

    def _open_media_progress_dialog(self) -> None:
        if self.current_game is None:
            return
        if self.current_game.media_type == "Фильмы":
            value, accepted = QInputDialog.getInt(self, "Просмотры", "Сколько раз вы посмотрели фильм?", self.current_game.watch_count, 0, 999)
            if accepted:
                self.current_game.watch_count = value
                self.current_game.history.append(f"{datetime.now():%d.%m.%Y %H:%M} — просмотров: {value}")
                self._configure_media_progress(self.current_game); self._refresh_history(); self.playtime_changed.emit(self.current_game, self.current_game.playtime_hours)
            return
        if self.current_game.media_type == "Сериалы":
            states = request_series_progress(
                self.current_game.seasons or 1,
                self.current_game.episode_states,
                self,
            )
            if states is not None:
                self.current_game.episode_states = states
                marked = []
                for key, state in states.items():
                    if state in ("watched", "watching"):
                        season, episode = (int(value) for value in key.split(":"))
                        marked.append((season, episode))
                self.current_game.season_number, self.current_game.episode_number = max(marked, default=(0, 0))
                total = max(1, self.current_game.seasons or 1) * 10
                watched = sum(state == "watched" for state in states.values())
                if any(state == "watching" for state in states.values()):
                    status = "СМОТРЮ"
                elif any(state == "dropped" for state in states.values()):
                    status = "БРОСИЛ"
                elif watched >= total:
                    status = "ПОСМОТРЕЛ"
                elif watched:
                    status = "СМОТРЮ"
                else:
                    status = "НЕ СМОТРЕЛ"
                self.current_game.history.append(
                    f"{datetime.now():%d.%m.%Y %H:%M} — серии: просмотрено {watched} из {total}"
                )
                self._change_status(status)
                self._configure_media_progress(self.current_game)
                self._refresh_history()
                self.playtime_changed.emit(self.current_game, self.current_game.playtime_hours)
            return
        total = request_total_playtime(self.current_game.playtime_hours, self)
        if total is not None: self._record_total_playtime(total)

    def _configure_media_progress(self, game: GameData) -> None:
        if game.media_type == "Фильмы":
            self.timeline_title.setText("ПРОСМОТРЫ И ХРОНОЛОГИЯ"); self.time_title.setText("ПРОСМОТРОВ"); self.time_button.setText("ИЗМЕНИТЬ КОЛИЧЕСТВО ПРОСМОТРОВ"); self.playtime.setText(str(game.watch_count))
        elif game.media_type == "Сериалы":
            watched = sum(state == "watched" for state in game.episode_states.values())
            total = max(1, game.seasons or 1) * 10
            self.timeline_title.setText("СЕРИИ И ХРОНОЛОГИЯ")
            self.time_title.setText("ПРОГРЕСС ПРОСМОТРА")
            self.time_button.setText("ОТКРЫТЬ СЕЗОНЫ И СЕРИИ")
            current = f" · S{game.season_number} E{game.episode_number}" if game.season_number else ""
            self.playtime.setText(f"{watched}/{total}{current}")
        elif game.media_type == "Программы":
            self.timeline_title.setText("ИСПОЛЬЗОВАНИЕ И ХРОНОЛОГИЯ"); self.time_title.setText("ВРЕМЯ ИСПОЛЬЗОВАНИЯ"); self.time_button.setText("ИЗМЕНИТЬ ВРЕМЯ ИСПОЛЬЗОВАНИЯ"); self.playtime.setText(self._format_hours(game.playtime_hours) if game.playtime_hours else "—")
        else:
            self.timeline_title.setText("ВРЕМЯ И ХРОНОЛОГИЯ"); self.time_title.setText("ВРЕМЯ В ИГРЕ"); self.time_button.setText("ИЗМЕНИТЬ ОБЩЕЕ ВРЕМЯ"); self.playtime.setText(self._format_hours(game.playtime_hours) if game.playtime_hours else "—")

    def _record_total_playtime(self, total_hours: float) -> None:
        if self.current_game is None or total_hours < 0:
            return
        current = self.current_game.playtime_hours
        difference = total_hours - current
        if abs(difference) < 0.05:
            return
        total_text = self._format_hours(total_hours)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.current_game.playtime_hours = total_hours
        change = f"+{difference:g} ч" if difference > 0 else f"коррекция {difference:g} ч"
        self.current_game.history.append(f"{timestamp} — всего {total_text} ({change})")
        self.playtime.setText(total_text)
        self._refresh_history()
        self.playtime_changed.emit(self.current_game, total_hours)

    def _refresh_history(self) -> None:
        if self.current_game is None or not self.current_game.history:
            self.history_label.setText("Изменений пока нет")
            return
        self.history_label.setText("\n".join(reversed(self.current_game.history[-2:])))

    @staticmethod
    def _parse_hours(value: str) -> float:
        try:
            return float(value.replace("ч", "").strip().replace(",", "."))
        except ValueError:
            return 0.0

    @staticmethod
    def _format_hours(value: float) -> str:
        return f"{value:.1f}".rstrip("0").rstrip(".") + " ч"

    def _toggle_favorite(self) -> None:
        if self.current_game is None:
            return
        selected = not self.current_game.favorite
        self.current_game.favorite = selected
        self.favorite_button.setText("★" if selected else "☆")
        self.favorite_button.setToolTip("Убрать из избранного" if selected else "Добавить в избранное")
        self.favorite_button.setStyleSheet(
            f"QPushButton {{ font-family:'Segoe UI Symbol'; font-size:16pt; padding:0; border:0; "
            f"background:transparent; color:{ACCENT if selected else '#F1F2F4'}; }}"
            f"QPushButton:hover {{ color:{ACCENT}; }}"
        )
        self.favorite_changed.emit(self.current_game, selected)

    def _request_detail(self) -> None:
        if self.current_game is not None:
            self.detail_requested.emit(self.current_game)

    def _request_hide(self) -> None:
        if self.current_game is not None:
            self.hidden_requested.emit(self.current_game)

    @staticmethod
    def _format_score(value: str) -> str:
        if value == "—":
            return value
        return value if "." in value else f"{value}.0"

    @staticmethod
    def _stars_for_score(value: str) -> str:
        try:
            score = max(0.0, min(10.0, float(value)))
        except ValueError:
            return "☆☆☆☆☆"
        filled = min(5, max(0, int((score + 1) // 2)))
        return "★" * filled + "☆" * (5 - filled)

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

    def _close(self) -> None:
        self.hide()
        self.closed.emit()
