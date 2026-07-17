from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.icon_registry import IconRegistry
from app.data.user_repository import LocalProfile
from app.ui.profile.profile_widgets import AvatarLabel


class ProfileOverview(QScrollArea):
    section_requested = Signal(int)
    catalog_item_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setMaximumWidth(1680)
        self.root = QVBoxLayout(content)
        self.root.setContentsMargins(8, 8, 8, 28)
        self.root.setSpacing(16)
        self._build_hero()
        self._build_summary()
        columns = QHBoxLayout()
        columns.setSpacing(16)
        self.recent_panel, self.recent_layout = self._panel("НЕДАВНЯЯ АКТИВНОСТЬ")
        self.favorite_panel, self.favorite_layout = self._panel("ИЗБРАННОЕ")
        columns.addWidget(self.recent_panel, 2)
        columns.addWidget(self.favorite_panel, 1)
        self.root.addLayout(columns)
        self.root.addStretch(1)
        self.setWidget(content)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    def _build_hero(self) -> None:
        hero = QFrame()
        hero.setObjectName("profileHero")
        hero.setStyleSheet(
            "QFrame#profileHero{background:#171126;border:1px solid #3B2855;border-radius:10px;}"
        )
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(22)
        self.avatar = AvatarLabel(138)
        layout.addWidget(self.avatar)
        identity = QVBoxLayout()
        identity.setSpacing(7)
        self.name = QLabel()
        self.name.setStyleSheet("font-size:24pt;font-weight:700;color:#F4F1F8;")
        identity.addWidget(self.name)
        self.subtitle = QLabel("Личная библиотека и история впечатлений")
        self.subtitle.setStyleSheet("font-size:11pt;color:#B9AFC8;")
        identity.addWidget(self.subtitle)
        privacy = QLabel("Все данные профиля хранятся только на этом компьютере")
        privacy.setStyleSheet("color:#8E829F;")
        identity.addWidget(privacy)
        identity.addStretch(1)
        layout.addLayout(identity, 1)
        edit = QPushButton("РЕДАКТИРОВАТЬ ПРОФИЛЬ")
        edit.setProperty("primary", True)
        edit.setMinimumSize(210, 40)
        edit.clicked.connect(lambda: self.section_requested.emit(4))
        layout.addWidget(edit, 0, Qt.AlignmentFlag.AlignTop)
        self.root.addWidget(hero)

    def _build_summary(self) -> None:
        panel, layout = self._panel("МОЯ БИБЛИОТЕКА")
        grid = QGridLayout()
        grid.setSpacing(10)
        self.summary_values = {}
        specs = (
            ("rated", "Оценено", "personal_rating", "#FFC42E"),
            ("favorites", "В избранном", "notification_bell", "#EC2B78"),
            ("completed", "Завершено", "date_completed", "#18D166"),
            ("hours", "Часов в играх", "playtime", "#4DA3FF"),
        )
        for column, (key, title, icon_id, color) in enumerate(specs):
            card = QFrame()
            card.setObjectName("profileSummaryCard")
            card.setStyleSheet(
                "QFrame#profileSummaryCard{background:#121221;border:1px solid #2A2940;border-radius:7px;}"
                "QFrame#profileSummaryCard:hover{background:#17102B;border-color:#7130A9;}"
            )
            card_layout = QHBoxLayout(card)
            icon = QLabel()
            icon.setFixedSize(32, 32)
            icon.setPixmap(IconRegistry.tinted_pixmap(icon_id, 26, color))
            card_layout.addWidget(icon)
            box = QVBoxLayout()
            value = QLabel("0")
            value.setStyleSheet(f"font-size:20pt;font-weight:750;color:{color};")
            box.addWidget(value)
            label = QLabel(title)
            label.setStyleSheet("color:#BFC0CD;")
            box.addWidget(label)
            card_layout.addLayout(box, 1)
            grid.addWidget(card, 0, column)
            self.summary_values[key] = value
        layout.addLayout(grid)
        links = QHBoxLayout()
        for text, index in (("МОИ ОЦЕНКИ", 1), ("ИЗБРАННОЕ", 2), ("СТАТИСТИКА", 3)):
            button = QPushButton(text)
            button.setObjectName("profileSectionLink")
            button.setMinimumHeight(36)
            button.clicked.connect(lambda checked=False, tab=index: self.section_requested.emit(tab))
            links.addWidget(button)
        links.addStretch(1)
        layout.addLayout(links)
        self.root.addWidget(panel)

    @staticmethod
    def _panel(title: str) -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("profilePanel")
        panel.setStyleSheet("QFrame#profilePanel{background:#111222;border:1px solid #292A43;border-radius:8px;}")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setStyleSheet("font-size:11pt;font-weight:700;color:#ECEAF1;")
        layout.addWidget(heading)
        return panel, layout

    @staticmethod
    def _clear_after_heading(layout: QVBoxLayout) -> None:
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self, profile: LocalProfile, games) -> None:
        games = list(games)
        interacted = [game for game in games if game.user_interacted]
        rated = [game for game in interacted if game.personal_score != "—"]
        favorites = [game for game in interacted if game.favorite]
        completed_statuses = {"ПРОШЁЛ", "ПОСМОТРЕЛ", "ИСПОЛЬЗОВАЛ"}
        completed = [game for game in interacted if game.status in completed_statuses]
        self.name.setText(profile.display_name)
        self.avatar.set_avatar(profile.avatar_path)
        self.summary_values["rated"].setText(str(len(rated)))
        self.summary_values["favorites"].setText(str(len(favorites)))
        self.summary_values["completed"].setText(str(len(completed)))
        self.summary_values["hours"].setText(f"{sum(g.playtime_hours for g in interacted):g}")
        self._fill_activity(interacted)
        self._fill_favorites(favorites)

    def _fill_activity(self, games) -> None:
        self._clear_after_heading(self.recent_layout)
        recent = sorted(games, key=lambda game: (len(game.history), game.interaction_started_at), reverse=True)[:6]
        if not recent:
            self.recent_layout.addWidget(self._empty("Здесь появятся ваши последние оценки и изменения статуса"))
            return
        for game in recent:
            row = QFrame()
            row.setObjectName("profileActivityRow")
            row.setStyleSheet(
                "QFrame#profileActivityRow{background:#0D0D19;border:0;border-bottom:1px solid #29283B;}"
                "QFrame#profileActivityRow:hover{background:#160B24;border-bottom-color:#7130A9;}"
            )
            layout = QHBoxLayout(row)
            kind = QLabel(game.media_type)
            kind.setStyleSheet("color:#A95CFF;font-weight:650;")
            kind.setFixedWidth(95)
            layout.addWidget(kind)
            title = QPushButton(game.title)
            title.setObjectName("profileObjectLink")
            title.setCursor(Qt.CursorShape.PointingHandCursor)
            title.setToolTip("Открыть карточку")
            title.clicked.connect(lambda checked=False, catalog_id=game.catalog_id: self.catalog_item_requested.emit(catalog_id))
            layout.addWidget(title, 1)
            score = QLabel(game.personal_score)
            score.setStyleSheet("font-size:13pt;font-weight:700;color:#FFC42E;")
            layout.addWidget(score)
            status = QLabel(game.status)
            status.setStyleSheet("color:#AAB0BC;")
            status.setMinimumWidth(130)
            status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(status)
            self.recent_layout.addWidget(row)

    def _fill_favorites(self, games) -> None:
        self._clear_after_heading(self.favorite_layout)
        if not games:
            self.favorite_layout.addWidget(self._empty("Добавляйте объекты в избранное — они появятся здесь"))
            return
        counts = Counter(game.media_type for game in games)
        summary = QLabel(" · ".join(f"{name}: {value}" for name, value in counts.items()))
        summary.setStyleSheet("color:#AFA7BC;")
        self.favorite_layout.addWidget(summary)
        for game in games[:6]:
            row = QPushButton(f"★  {game.title}   {game.personal_score}")
            row.setObjectName("profileObjectLink")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.clicked.connect(lambda checked=False, catalog_id=game.catalog_id: self.catalog_item_requested.emit(catalog_id))
            self.favorite_layout.addWidget(row)
        more = QPushButton("ОТКРЫТЬ ВСЁ ИЗБРАННОЕ")
        more.clicked.connect(lambda: self.section_requested.emit(2))
        self.favorite_layout.addWidget(more)

    @staticmethod
    def _empty(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("padding:22px;color:#8F91A0;")
        return label
