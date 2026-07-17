from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.icon_registry import IconRegistry


class RankedBarList(QWidget):
    """Compact ranked values with optional registry icons and proportional bars."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 6, 0, 0)
        self._layout.setSpacing(7)
        self.setMinimumHeight(190)

    def set_items(
        self,
        items: Iterable[tuple[str, float]],
        *,
        maximum: float | None = None,
        color: str = "#8B2CF5",
        formatter: Callable[[float], str] | None = None,
        icon_resolver: Callable[[str], tuple[str, str | None] | None] | None = None,
        empty_text: str = "Нет данных",
    ) -> None:
        self._clear()
        values = list(items)
        if not values:
            label = QLabel(empty_text)
            label.setObjectName("muted")
            label.setWordWrap(True)
            self._layout.addWidget(label)
            self._layout.addStretch(1)
            return
        scale = maximum if maximum is not None else max(value for _, value in values)
        for name, value in values:
            row = QWidget()
            row.setStyleSheet("background:transparent;border:0;")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            if icon_resolver:
                icon_spec = icon_resolver(name)
                if icon_spec:
                    icon_id, category = icon_spec
                    icon = QLabel()
                    icon.setFixedSize(21, 21)
                    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    icon.setPixmap(
                        IconRegistry.pixmap(icon_id, 18, variant="dark", category=category)
                    )
                    layout.addWidget(icon)
            title = QLabel(name)
            title.setMinimumWidth(94)
            title.setMaximumWidth(150)
            title.setToolTip(name)
            title.setStyleSheet("color:#E4E5ED;background:transparent;border:0;")
            layout.addWidget(title)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(round((value / max(scale, 0.001)) * 1000))
            bar.setTextVisible(False)
            bar.setFixedHeight(9)
            bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            bar.setStyleSheet(
                "QProgressBar{background:#28293C;border:0;border-radius:2px;}"
                f"QProgressBar::chunk{{background:{color};border-radius:2px;}}"
            )
            layout.addWidget(bar, 1)
            shown = formatter(value) if formatter else f"{value:g}"
            number = QLabel(shown)
            number.setFixedWidth(48)
            number.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            number.setStyleSheet(
                f"font-size:12pt;font-weight:700;color:{color};background:transparent;border:0;"
            )
            layout.addWidget(number)
            self._layout.addWidget(row)
        self._layout.addStretch(1)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

