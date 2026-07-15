from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
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


EPISODES_PER_SEASON = 10

STATE_META = {
    "unwatched": ("Не просмотрено", "#77839a", "#202936"),
    "watched": ("Просмотрено", "#21d46b", "#123b28"),
    "watching": ("Смотрю", "#ffc400", "#44380a"),
    "dropped": ("Бросил", "#ff4b4b", "#431b21"),
}


class SeriesProgressDialog(QDialog):
    """Visual season/episode editor with a status paint palette."""

    def __init__(self, total_seasons: int, states: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Прогресс сериала")
        self.setWindowIcon(IconRegistry.icon("video_media", variant="dark", category="media"))
        self.setMinimumSize(820, 560)
        self.resize(980, 650)
        self.total_seasons = max(1, total_seasons)
        self.states = dict(states)
        self.active_state = "watched"
        self.tiles: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)
        title = QLabel("СЕЗОНЫ И СЕРИИ")
        title.setStyleSheet("font-size: 18pt; font-weight: 700;")
        root.addWidget(title)
        hint = QLabel("Выберите состояние справа, затем нажимайте на серии. Повторный клик серой кистью очищает отметку.")
        hint.setObjectName("muted")
        root.addWidget(hint)

        content = QHBoxLayout()
        content.setSpacing(18)
        content.addWidget(self._build_episode_grid(), 1)
        content.addWidget(self._build_palette())
        root.addLayout(content, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить прогресс")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._refresh_palette()
        self._refresh_counts()

    def _build_episode_grid(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 0, 8, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        corner = QLabel("СЕРИЯ")
        corner.setObjectName("muted")
        grid.addWidget(corner, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        for season in range(1, self.total_seasons + 1):
            label = QLabel(f"СЕЗОН {season}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: 600; color: #c8d0dc;")
            grid.addWidget(label, 0, season)

        for episode in range(1, EPISODES_PER_SEASON + 1):
            row_label = QLabel(f"E{episode}")
            row_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_label.setObjectName("muted")
            grid.addWidget(row_label, episode, 0)
            for season in range(1, self.total_seasons + 1):
                key = f"{season}:{episode}"
                tile = QPushButton(str(episode))
                tile.setMinimumSize(72, 44)
                tile.setToolTip(f"Сезон {season}, серия {episode}")
                tile.clicked.connect(lambda _checked=False, item=key: self._paint(item))
                self.tiles[key] = tile
                grid.addWidget(tile, episode, season)
                self._style_tile(key)
        grid.setColumnStretch(self.total_seasons + 1, 1)
        scroll.setWidget(host)
        return scroll

    def _build_palette(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("seriesLegend")
        panel.setFixedWidth(245)
        panel.setStyleSheet("#seriesLegend { background:#0b151e; border:1px solid #213443; border-radius:10px; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        heading = QLabel("СТАТУС СЕРИИ")
        heading.setStyleSheet("font-weight:700;")
        layout.addWidget(heading)
        note = QLabel("Выберите цвет и заполните плитки")
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)

        self.palette_group = QButtonGroup(self)
        self.palette_group.setExclusive(True)
        self.palette_buttons: dict[str, QPushButton] = {}
        for state, (label, color, _background) in STATE_META.items():
            button = QPushButton(f"●  {label}")
            button.setCheckable(True)
            button.setMinimumHeight(38)
            button.clicked.connect(lambda _checked=False, value=state: self._select_state(value))
            button.setStyleSheet(f"text-align:left; padding-left:12px; color:{color};")
            self.palette_group.addButton(button)
            self.palette_buttons[state] = button
            layout.addWidget(button)

        layout.addSpacing(8)
        self.counts_label = QLabel()
        self.counts_label.setWordWrap(True)
        self.counts_label.setObjectName("muted")
        layout.addWidget(self.counts_label)
        layout.addStretch(1)
        apply_all = QPushButton("Применить ко всем сериям")
        apply_all.setMinimumHeight(38)
        apply_all.clicked.connect(self._apply_to_all)
        layout.addWidget(apply_all)
        clear = QPushButton("Очистить все")
        clear.clicked.connect(self._clear_all)
        layout.addWidget(clear)
        return panel

    def _select_state(self, state: str) -> None:
        self.active_state = state
        self._refresh_palette()

    def _refresh_palette(self) -> None:
        for state, button in self.palette_buttons.items():
            label, color, background = STATE_META[state]
            active = state == self.active_state
            button.setChecked(active)
            button.setStyleSheet(
                f"text-align:left; padding-left:12px; color:{color}; "
                f"background:{background if active else '#0b151e'}; "
                f"border:1px solid {color if active else '#263746'}; border-radius:7px; font-weight:{700 if active else 500};"
            )

    def _paint(self, key: str) -> None:
        if self.active_state == "unwatched":
            self.states.pop(key, None)
        else:
            self.states[key] = self.active_state
        self._style_tile(key)
        self._refresh_counts()

    def _style_tile(self, key: str) -> None:
        state = self.states.get(key, "unwatched")
        _label, color, background = STATE_META.get(state, STATE_META["unwatched"])
        self.tiles[key].setStyleSheet(
            f"QPushButton {{ color:{color}; background:{background}; border:1px solid {color}; "
            "border-radius:7px; font-size:11pt; font-weight:650; } "
            "QPushButton:hover { border:2px solid #ffffff; }"
        )

    def _apply_to_all(self) -> None:
        for key in self.tiles:
            if self.active_state == "unwatched":
                self.states.pop(key, None)
            else:
                self.states[key] = self.active_state
            self._style_tile(key)
        self._refresh_counts()

    def _clear_all(self) -> None:
        self.active_state = "unwatched"
        self._refresh_palette()
        self._apply_to_all()

    def _refresh_counts(self) -> None:
        counts = Counter(self.states.values())
        total = self.total_seasons * EPISODES_PER_SEASON
        marked = sum(counts.values())
        self.counts_label.setText(
            f"Просмотрено: {counts['watched']}\n"
            f"Смотрю: {counts['watching']}\n"
            f"Брошено: {counts['dropped']}\n"
            f"Без отметки: {max(0, total - marked)}"
        )

    def result_states(self) -> dict[str, str]:
        return {key: state for key, state in self.states.items() if state != "unwatched"}


def request_series_progress(total_seasons: int, states: dict[str, str], parent=None) -> dict[str, str] | None:
    dialog = SeriesProgressDialog(total_seasons, states, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.result_states()
