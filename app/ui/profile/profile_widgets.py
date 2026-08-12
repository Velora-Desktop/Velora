from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTabBar, QWidget

from app.core.paths import USER_IMAGES_DIR
from app.ui.velora_ui.components import HoverAnimatedIcon


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
        self.setObjectName("profileAvatarLabel")
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "QLabel#profileAvatarLabel{background:#151526;"
            "border:2px solid #8040C8;border-radius:8px;}"
        )
        animated_size = size - 12
        self._default_avatar = HoverAnimatedIcon(
            "animated.user_avatar",
            animated_size,
            self,
            display_width=animated_size,
            frame_interval_ms=40,
            autoplay=True,
            mouse_transparent=True,
        )
        self._default_avatar.setObjectName("animatedDefaultAvatar")
        self._default_avatar.move(6, 6)
        self.set_avatar("")

    def set_avatar(self, path: str) -> None:
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            self.clear()
            self._default_avatar.show()
            self._default_avatar.raise_()
        else:
            self._default_avatar.hide()
            self.setPixmap(
                pixmap.scaled(
                    self._avatar_size - 12,
                    self._avatar_size - 12,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


class AvatarPicker(QWidget):
    """Extensible avatar choice strip: custom upload plus built-in avatars."""

    custom_avatar_requested = Signal()
    avatar_selected = Signal(str)

    def __init__(self, avatar_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self._avatar_path = avatar_path
        self._custom_avatar_path = avatar_path
        self.setObjectName("profileAvatarPicker")
        self.setMinimumHeight(184)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.custom_button = QPushButton("+")
        self.custom_button.setObjectName("customAvatarChoice")
        self.custom_button.setToolTip("Добавить свой аватар")
        self.custom_button.setFixedSize(176, 176)
        self.custom_button.clicked.connect(self._select_custom)
        layout.addWidget(self.custom_button)

        self.default_button = QPushButton()
        self.default_button.setObjectName("defaultAvatarChoice")
        self.default_button.setToolTip("Стандартный аватар Velora")
        self.default_button.setFixedSize(176, 176)
        default_layout = QHBoxLayout(self.default_button)
        default_layout.setContentsMargins(10, 10, 10, 10)
        self.default_animation = HoverAnimatedIcon(
            "animated.user_avatar", 156, self.default_button,
            display_width=156, frame_interval_ms=40, autoplay=True,
            mouse_transparent=True,
        )
        self.default_animation.setObjectName("avatarPickerDefaultAnimation")
        default_layout.addWidget(self.default_animation, 0, Qt.AlignmentFlag.AlignCenter)
        self.default_button.clicked.connect(self._select_default)
        layout.addWidget(self.default_button)
        layout.addStretch(1)

        self.setStyleSheet(
            "QPushButton#customAvatarChoice,QPushButton#defaultAvatarChoice{"
            "background:#101822;border:1px solid #2B3945;border-radius:9px;"
            "padding:0;color:#DDE3E8;}"
            "QPushButton#customAvatarChoice{font-size:64px;font-weight:300;}"
            "QPushButton#customAvatarChoice:hover,QPushButton#defaultAvatarChoice:hover{"
            "background:#1A0D2B;border-color:#8B2CF5;color:#D7A8FF;}"
            "QPushButton#customAvatarChoice[selected=\"true\"],"
            "QPushButton#defaultAvatarChoice[selected=\"true\"]{background:#1A0D2B;"
            "border:2px solid #A54BFF;}"
        )
        self._refresh_custom_preview()
        self._refresh_selection()

    @property
    def avatar_path(self) -> str:
        return self._avatar_path

    def set_custom_avatar(self, path: str) -> None:
        self._avatar_path = path
        self._custom_avatar_path = path
        self._refresh_custom_preview()
        self._refresh_selection()
        self.avatar_selected.emit(path)

    def _select_custom(self) -> None:
        if not self._custom_avatar_path:
            self.custom_avatar_requested.emit()
            return
        self._avatar_path = self._custom_avatar_path
        self._refresh_selection()
        self.avatar_selected.emit(self._avatar_path)

    def _select_default(self) -> None:
        self._avatar_path = ""
        self._refresh_selection()
        self.avatar_selected.emit("")

    def _refresh_custom_preview(self) -> None:
        pixmap = QPixmap(self._custom_avatar_path)
        if pixmap.isNull():
            self.custom_button.setIcon(QIcon())
            self.custom_button.setText("+")
            return
        preview_size = 156
        scaled = pixmap.scaled(
            preview_size,
            preview_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - preview_size) // 2)
        y = max(0, (scaled.height() - preview_size) // 2)
        self.custom_button.setText("")
        self.custom_button.setIcon(QIcon(scaled.copy(x, y, preview_size, preview_size)))
        self.custom_button.setIconSize(QSize(preview_size, preview_size))

    def _refresh_selection(self) -> None:
        for button, selected in (
            (self.custom_button, bool(self._avatar_path)),
            (self.default_button, not self._avatar_path),
        ):
            button.setProperty("selected", selected)
            button.style().unpolish(button)
            button.style().polish(button)


class GlowingTabBar(QTabBar):
    """Velora tab bar using the shared underline selection treatment."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("profileTabBar")
        self.setDrawBase(False)
        self.setExpanding(False)
