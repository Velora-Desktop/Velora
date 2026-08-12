"""Shared search field with a non-blocking hover animation."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit

from .animated_icon import HoverAnimatedIcon


class AnimatedSearchLineEdit(QLineEdit):
    def __init__(self, parent=None, *, icon_size: int = 19) -> None:
        super().__init__(parent)
        self.search_icon = HoverAnimatedIcon(
            "animated.search", icon_size, self, mouse_transparent=True
        )
        self.search_icon.setObjectName("animatedSearchIcon")
        self.search_icon.attach_hover_source(self)
        self.setTextMargins(0, 0, icon_size + 14, 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        margin = 10
        self.search_icon.move(
            self.width() - self.search_icon.width() - margin,
            (self.height() - self.search_icon.height()) // 2,
        )
