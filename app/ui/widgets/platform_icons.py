from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.core.icon_registry import IconRegistry


PLATFORM_ALIASES = {
    "PC": ("pc", "PC"),
    "WINDOWS": ("windows", "Windows"),
    "WIN": ("windows", "Windows"),
    "PLAYSTATION": ("playstation", "PlayStation"),
    "PS": ("playstation", "PlayStation"),
    "XBOX": ("xbox", "Xbox"),
    "XONE": ("xbox", "Xbox One"),
    "X360": ("xbox", "Xbox 360"),
    "SWITCH": ("nintendo_switch", "Nintendo Switch"),
    "NINTENDO": ("nintendo_switch", "Nintendo"),
    "LINUX": ("linux", "Linux"),
    "ANDROID": ("android", "Android"),
    "IOS": ("apple", "iOS"),
    "IPHONE": ("apple", "iPhone"),
    "MAC": ("apple", "macOS"),
    "APPLE": ("apple", "Apple"),
    "STEAM": ("gaming_pc", "Steam"),
    "STEAM DECK": ("gaming_pc", "Steam Deck"),
    "VR": ("vr", "VR"),
}


def platform_tokens(value: str) -> list[str]:
    return [token.strip() for token in re.split(r"[;,/]", value or "") if token.strip()]


def platform_icon(token: str) -> tuple[str, str]:
    upper = token.upper()
    for prefix, result in PLATFORM_ALIASES.items():
        if upper == prefix or upper.startswith(prefix):
            return result[0], token
    return "gaming_pc", token


class PlatformIconRow(QWidget):
    def __init__(self, platforms: str = "", *, colored: bool = False, max_icons: int = 3, centered: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._colored = colored
        self._max_icons = max_icons
        self._centered = centered
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)
        self.set_platforms(platforms)

    def set_platforms(self, platforms: str) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        tokens = platform_tokens(platforms)
        # Different textual aliases may represent the same visual platform
        # (for example iOS/iPhone or Windows/PC).  Keep one icon per family.
        unique_tokens = []
        seen_icons = set()
        for token in tokens:
            icon_id, _ = platform_icon(token)
            family = "windows_pc" if icon_id in {"windows", "pc"} else icon_id
            if family in seen_icons:
                continue
            seen_icons.add(family)
            unique_tokens.append(token)
        tokens = unique_tokens
        if self._centered:
            self._layout.addStretch(1)
        for token in tokens[: self._max_icons]:
            icon_id, tooltip = platform_icon(token)
            label = QLabel()
            label.setFixedSize(19, 19)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(IconRegistry.pixmap(icon_id, 17, variant="color" if self._colored else "dark", category="platforms"))
            label.setToolTip(tooltip)
            self._layout.addWidget(label)
        if len(tokens) > self._max_icons:
            extra = QLabel(f"+{len(tokens) - self._max_icons}")
            extra.setToolTip(", ".join(tokens[self._max_icons :]))
            extra.setObjectName("muted")
            self._layout.addWidget(extra)
        if not tokens:
            self._layout.addWidget(QLabel("—"))
        self._layout.addStretch(1)

    def setText(self, platforms: str) -> None:
        """QLabel-compatible update hook for metadata panels."""
        self.set_platforms(platforms)
