from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QPushButton, QWidgetAction

from app.core.constants import DANGER, SUCCESS, WARNING
from app.ui.catalog.game_row import GAME_STATUSES


STATUS_COLORS = {
    "НЕ НАЧИНАЛ": "#808891",
    "ПРОХОЖУ": WARNING,
    "ПРОШЁЛ": SUCCESS,
    "БРОСИЛ": DANGER,
}


def build_status_menu(parent, callback: Callable[[str], None]) -> QMenu:
    menu = QMenu(parent)
    menu.setStyleSheet("QMenu { background:#171207; border:1px solid #5A4208; padding:5px; }")
    for status in GAME_STATUSES:
        action = QWidgetAction(menu)
        button = QPushButton(status)
        color = STATUS_COLORS[status]
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
