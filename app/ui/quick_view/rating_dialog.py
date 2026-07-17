from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.icon_registry import IconRegistry
from app.ui.quick_view.series_progress_dialog import request_series_progress


GAME_CRITERIA = (
    ("Графика", "graphics.svg"),
    ("Саундтрек", "soundtrack.svg"),
    ("Сюжет", "story.svg"),
    ("Геймплей", "gameplay.svg"),
    ("Атмосфера", "atmosphere.svg"),
)

CRITERIA_BY_MEDIA = {
    "Игры": GAME_CRITERIA,
    "Фильмы": (
        ("Сюжет", "story.svg"),
        ("Актёрская игра", "atmosphere.svg"),
        ("Режиссура", "gameplay.svg"),
        ("Саундтрек", "soundtrack.svg"),
        ("Визуал", "graphics.svg"),
    ),
    "Сериалы": (
        ("Сюжет", "story.svg"),
        ("Персонажи", "atmosphere.svg"),
        ("Темп", "gameplay.svg"),
        ("Саундтрек", "soundtrack.svg"),
        ("Визуал", "graphics.svg"),
    ),
    "Программы": (
        ("Функциональность", "gameplay.svg"),
        ("Удобство", "atmosphere.svg"),
        ("Интерфейс", "graphics.svg"),
        ("Стабильность", "story.svg"),
        ("Производительность", "soundtrack.svg"),
    ),
}


@dataclass(frozen=True)
class RatingResult:
    criteria: dict[str, int]
    total_hours: float
    watch_count: int
    episode_states: dict[str, str]


def _series_summary(total_seasons: int, states: dict[str, str]) -> str:
    watched = sum(state == "watched" for state in states.values())
    active = []
    for key, state in states.items():
        if state in ("watched", "watching"):
            season, episode = (int(value) for value in key.split(":"))
            active.append((season, episode))
    current = max(active, default=(0, 0))
    total = max(1, total_seasons) * 10
    suffix = f" · S{current[0]} E{current[1]}" if current[0] else ""
    return f"Просмотрено серий: {watched}/{total}{suffix}"


def request_rating(
    current: dict[str, int],
    parent=None,
    media_type: str = "Игры",
    current_hours: float = 0.0,
    watch_count: int = 0,
    seasons: int = 1,
    episode_states: dict[str, str] | None = None,
) -> RatingResult | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Моя оценка")
    dialog.setWindowIcon(IconRegistry.icon("edit", category="ui"))
    dialog.setMinimumWidth(640)

    root = QVBoxLayout(dialog)
    root.setContentsMargins(22, 18, 22, 18)
    root.setSpacing(12)
    title = QLabel("ОЦЕНИТЕ ОБЪЕКТ")
    title.setStyleSheet("font-size:17pt;font-weight:700;")
    root.addWidget(title)
    hint = QLabel("Перемещайте ползунки от 1 до 10. Средняя оценка рассчитывается сразу.")
    hint.setObjectName("muted")
    root.addWidget(hint)

    editors: dict[str, QSlider] = {}
    values: dict[str, QLabel] = {}
    for name, icon_name in CRITERIA_BY_MEDIA.get(media_type, GAME_CRITERIA):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(28, 28)
        icon.setPixmap(IconRegistry.pixmap(icon_name.removesuffix(".svg"), 22, variant="svg", category="rating"))
        layout.addWidget(icon)
        label = QLabel(name)
        label.setMinimumWidth(105)
        label.setStyleSheet("font-size:11pt;font-weight:550;")
        layout.addWidget(label)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(1, 10)
        slider.setValue(current.get(name, 5))
        slider.setMinimumWidth(330)
        slider.setStyleSheet(
            "QSlider::groove:horizontal{height:7px;background:#252C35;border-radius:3px;}"
            "QSlider::sub-page:horizontal{background:#8B2CF5;border-radius:3px;}"
            "QSlider::handle:horizontal{width:18px;margin:-6px 0;background:#E7D7FF;"
            "border:2px solid #9D4CFF;border-radius:9px;}"
        )
        layout.addWidget(slider, 1)
        value = QLabel()
        value.setFixedWidth(58)
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value)
        editors[name] = slider
        values[name] = value
        root.addWidget(row)

    average_box = QWidget()
    average_box.setStyleSheet("background:#101923;border:1px solid #293844;border-radius:8px;")
    average_layout = QHBoxLayout(average_box)
    average_layout.addWidget(QLabel("СРЕДНЯЯ ОЦЕНКА"))
    average_layout.addStretch()
    average = QLabel()
    average_layout.addWidget(average)
    root.addWidget(average_box)

    def color(score: float) -> str:
        return "#18D647" if score >= 8 else "#FFC400" if score >= 5 else "#FF4B45"

    def refresh() -> None:
        for name, slider in editors.items():
            values[name].setText(f"{slider.value()}/10")
            values[name].setStyleSheet(f"font-size:12pt;font-weight:700;color:{color(slider.value())};")
        score = sum(slider.value() for slider in editors.values()) / len(editors)
        average.setText(f"{score:.1f}")
        average.setStyleSheet(f"font-size:24pt;font-weight:750;color:{color(score)};")

    for slider in editors.values():
        slider.valueChanged.connect(refresh)
    refresh()

    hours = QDoubleSpinBox()
    hours.setRange(0.0, 1_000_000.0)
    hours.setDecimals(1)
    hours.setSingleStep(0.5)
    hours.setValue(float(current_hours or 0.0))
    hours.setSuffix(" ч")
    hours.setMinimumWidth(180)
    hours.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
    hours.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if media_type == "Игры":
        metric_row = QHBoxLayout()
        metric_row.addWidget(QLabel("Общее время в игре"))
        metric_row.addStretch()
        decrease_hours = QPushButton("−")
        decrease_hours.setFixedSize(38, 38)
        decrease_hours.setToolTip("Уменьшить время на 0,5 часа")
        decrease_hours.clicked.connect(hours.stepDown)
        metric_row.addWidget(decrease_hours)
        metric_row.addWidget(hours)
        increase_hours = QPushButton("+")
        increase_hours.setFixedSize(38, 38)
        increase_hours.setToolTip("Увеличить время на 0,5 часа")
        increase_hours.clicked.connect(hours.stepUp)
        metric_row.addWidget(increase_hours)
        root.addLayout(metric_row)

    views = QSpinBox()
    views.setRange(0, 999)
    views.setValue(int(watch_count or 0))
    views.setMinimumWidth(180)
    views.setSuffix(" раз")
    views.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    views.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if media_type == "Фильмы":
        metric_row = QHBoxLayout()
        metric_row.addWidget(QLabel("Количество просмотров"))
        metric_row.addStretch()
        decrease_views = QPushButton("−")
        decrease_views.setFixedSize(38, 38)
        decrease_views.setToolTip("Уменьшить количество просмотров")
        decrease_views.clicked.connect(views.stepDown)
        metric_row.addWidget(decrease_views)
        metric_row.addWidget(views)
        increase_views = QPushButton("+")
        increase_views.setFixedSize(38, 38)
        increase_views.setToolTip("Увеличить количество просмотров")
        increase_views.clicked.connect(views.stepUp)
        metric_row.addWidget(increase_views)
        root.addLayout(metric_row)

    selected_states = dict(episode_states or {})
    series_summary = QLabel(_series_summary(seasons, selected_states))
    series_summary.setObjectName("muted")
    if media_type == "Сериалы":
        series_box = QWidget()
        series_box.setStyleSheet("background:#101923;border:1px solid #293844;border-radius:8px;")
        series_layout = QHBoxLayout(series_box)
        series_layout.addWidget(series_summary, 1)
        open_series = QPushButton("СЕЗОНЫ И СЕРИИ")
        open_series.setIcon(IconRegistry.icon("list", category="ui"))

        def edit_series_progress() -> None:
            nonlocal selected_states
            states = request_series_progress(max(1, seasons), selected_states, dialog)
            if states is not None:
                selected_states = states
                series_summary.setText(_series_summary(seasons, selected_states))

        open_series.clicked.connect(edit_series_progress)
        series_layout.addWidget(open_series)
        root.addWidget(series_box)

    actions = QHBoxLayout()
    actions.addStretch()
    cancel = QPushButton("ОТМЕНА")
    cancel.clicked.connect(dialog.reject)
    save = QPushButton("СОХРАНИТЬ ОЦЕНКУ")
    save.setProperty("primary", True)
    save.setIcon(IconRegistry.icon("save"))
    save.clicked.connect(dialog.accept)
    actions.addWidget(cancel)
    actions.addWidget(save)
    root.addLayout(actions)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return RatingResult(
        criteria={name: slider.value() for name, slider in editors.items()},
        total_hours=hours.value(),
        watch_count=views.value(),
        episode_states=selected_states,
    )
