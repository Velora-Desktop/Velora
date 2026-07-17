from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QTabBar

from app.core.icon_registry import IconRegistry
from app.core.paths import USER_IMAGES_DIR


PROFILE_IMAGES_DIR = USER_IMAGES_DIR / "profile"


def store_profile_avatar(source: str) -> str:
    """Copy a selected avatar into Velora's local profile storage."""
    path = Path(source)
    if not path.is_file():
        return ""
    PROFILE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
    destination = PROFILE_IMAGES_DIR / f"avatar{suffix}"
    if path.resolve() != destination.resolve():
        shutil.copy2(path, destination)
    return str(destination)


class AvatarLabel(QLabel):
    def __init__(self, size: int = 132, parent=None) -> None:
        super().__init__(parent)
        self._avatar_size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background:#151526;border:2px solid #8040C8;border-radius:8px;"
        )

    def set_avatar(self, path: str) -> None:
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            pixmap = IconRegistry.pixmap("user_data", self._avatar_size // 2, variant="dark")
        self.setPixmap(
            pixmap.scaled(
                self._avatar_size - 12,
                self._avatar_size - 12,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class GlowingTabBar(QTabBar):
    """Velora tab bar with a restrained glow around the selected workspace."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("profileTabBar")
        self.setDrawBase(False)
        self.setExpanding(False)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.currentIndex() < 0:
            return
        # The stylesheet owns the crisp selected border. Draw only one wide,
        # translucent outer halo so hover and selected borders never double.
        rect = self.tabRect(self.currentIndex()).adjusted(3, 3, -3, -4)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(151, 62, 255, 28), 7))
        painter.drawRoundedRect(rect, 5, 5)
        painter.end()
