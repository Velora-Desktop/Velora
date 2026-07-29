from collections.abc import Callable

from PySide6.QtCore import Qt
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

_STATUS_BUTTON_STYLE = """
QPushButton#veloraStatusButton {
    color:#8A929A;
    border:1px solid #38434D;
    border-radius:5px;
    background:#111820;
    font-weight:600;
    padding:3px 22px 3px 8px;
    text-align:center;
}
QPushButton#veloraStatusButton[statusKind="active"] {
    color:#FFCC00;
    border-color:#775000;
    background:#251A07;
}
QPushButton#veloraStatusButton[statusKind="success"] {
    color:#13D56B;
    border-color:#1B6D35;
    background:#092013;
}
QPushButton#veloraStatusButton[statusKind="danger"] {
    color:#FF4A4A;
    border-color:#7A2828;
    background:#251010;
}
QPushButton#veloraStatusButton:hover {
    border-color:#A54BFF;
}
QPushButton#veloraStatusButton:focus {
    border-color:#A54BFF;
}
QPushButton#veloraStatusButton::menu-indicator {
    subcontrol-position:right center;
    right:8px;
}
"""


def _status_kind(status: str) -> str:
    color, _border, _background = status_visual(status)
    if color == SUCCESS:
        return "success"
    if color == WARNING or status == "ЖДУ НОВЫЙ СЕЗОН":
        return "active"
    if color == DANGER:
        return "danger"
    return "neutral"


class StatusButton(QPushButton):
    """Persistent status control shared by every game presentation.

    Status changes update a dynamic property on the existing button.  The
    widget, its geometry, menu and stylesheet are not replaced during normal
    state changes, preventing native/unstyled surfaces from flashing between
    adjacent catalog cells.
    """

    def __init__(
        self,
        callback: Callable[[str], None],
        media_type: str = "Игры",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._callback = callback
        self._media_type = ""
        self._status_value = ""
        self.setObjectName("veloraStatusButton")
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setStyleSheet(_STATUS_BUTTON_STYLE)
        self.set_media_type(media_type)

    @property
    def status_value(self) -> str:
        return self._status_value

    def set_status(self, status: str) -> None:
        status = status or "НЕ НАЧИНАЛ"
        kind = _status_kind(status)
        text_changed = self.text() != status
        kind_changed = self.property("statusKind") != kind
        self._status_value = status
        if text_changed:
            self.setText(status)
        if kind_changed:
            self.setUpdatesEnabled(False)
            self.setProperty("statusKind", kind)
            style = self.style()
            style.unpolish(self)
            style.polish(self)
            self.setUpdatesEnabled(True)
        if text_changed or kind_changed:
            self.update()

    def set_media_type(self, media_type: str) -> None:
        if media_type == self._media_type and self.menu() is not None:
            return
        old_menu = self.menu()
        self._media_type = media_type
        self.setMenu(build_status_menu(self, self._callback, media_type))
        if old_menu is not None:
            old_menu.deleteLater()


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
