from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QPushButton, QWidgetAction

from app.core.constants import DANGER, SUCCESS, WARNING
from app.models.game import MEDIA_STATUSES
from app.core.icon_registry import IconRegistry


STATUS_COLORS = {
    "НЕ НАЧИНАЛ": "#808891",
    "ПРОХОЖУ": WARNING,
    "ПРОШЁЛ": SUCCESS,
    "БРОСИЛ": DANGER,
    "СМОТРЮ": WARNING,
    "ПОСМОТРЕЛ": SUCCESS,
    "ЖДУ НОВЫЙ СЕЗОН": "#4DA3FF",
    "ИСПОЛЬЗУЮ": WARNING,
    "ИСПОЛЬЗОВАЛ": SUCCESS,
    "УДАЛИЛ": DANGER,
    "ОТКАЗАЛСЯ": DANGER,
}

STATUS_ICONS = {
    "НЕ НАЧИНАЛ": "not_started", "ПРОХОЖУ": "playing", "ПРОШЁЛ": "completed", "БРОСИЛ": "dropped",
    "НЕ СМОТРЕЛ": "not_watched", "СМОТРЮ": "watching", "ПОСМОТРЕЛ": "watched", "ЖДУ НОВЫЙ СЕЗОН": "waiting_new_season",
    "НЕ ИСПОЛЬЗОВАЛ": "not_used", "ИСПОЛЬЗУЮ": "using", "ИСПОЛЬЗОВАЛ": "used", "ОТКАЗАЛСЯ": "abandoned",
}


def status_visual(status: str) -> tuple[str, str, str]:
    if status in {"ПРОШЁЛ", "ПОСМОТРЕЛ", "ИСПОЛЬЗОВАЛ"}:
        return SUCCESS, "#1B6D35", "#092013"
    if status in {"ПРОХОЖУ", "СМОТРЮ", "ИСПОЛЬЗУЮ", "ЖДУ НОВЫЙ СЕЗОН"}:
        return WARNING, "#775000", "#251A07"
    if status in {"БРОСИЛ", "УДАЛИЛ", "ОТКАЗАЛСЯ"}:
        return DANGER, "#7A2828", "#251010"
    return "#8A929A", "#38434D", "#111820"


def build_status_menu(parent, callback: Callable[[str], None], media_type: str = "Игры") -> QMenu:
    menu = QMenu(parent)
    menu.setStyleSheet("QMenu { background:#171207; border:1px solid #5A4208; padding:5px; }")
    for status in MEDIA_STATUSES.get(media_type, MEDIA_STATUSES["Игры"]):
        action = QWidgetAction(menu)
        button = QPushButton(status)
        button.setIcon(IconRegistry.icon(STATUS_ICONS.get(status, "activity")))
        # Keep dropdown entries synchronized with catalog, Quick View and
        # detail-page status colors.
        color = status_visual(status)[0]
        button.setStyleSheet(
            f"QPushButton {{ color:{color}; text-align:left; border:0; border-radius:4px; "
            "background:transparent; padding:7px 12px; min-width:125px; }"
            "QPushButton:hover { background:#2A230F; }"
        )
        button.clicked.connect(lambda checked=False, value=status: _choose(menu, callback, value))
        action.setDefaultWidget(button)
        menu.addAction(action)
    return menu


def _choose(menu: QMenu, callback: Callable[[str], None], status: str) -> None:
    menu.close()
    callback(status)
