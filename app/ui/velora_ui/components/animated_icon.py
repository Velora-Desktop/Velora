"""Reusable hover-triggered animated icon with a safe static fallback."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import QLabel
from shiboken6 import isValid

from app.core.icon_registry import IconRegistry
from app.ui.velora_ui.motion import reduced_motion_enabled


class HoverAnimatedIcon(QLabel):
    def __init__(
        self,
        key: str,
        size: int = 20,
        parent=None,
        *,
        idle_frame: int | None = None,
        mouse_transparent: bool = False,
        display_width: int | None = None,
        frame_interval_ms: int = 17,
        autoplay: bool = False,
    ) -> None:
        super().__init__(parent)
        self._key = key
        self._size = int(size)
        self._display_width = int(display_width or size)
        self._idle_frame = (
            12 if idle_frame is None and key == "service.netflix"
            else int(idle_frame or 0)
        )
        self._idle_key = (
            "service.netflix.idle" if key == "service.netflix" else None
        )
        self._autoplay = bool(autoplay)
        self._movie: QMovie | None = None
        self._sequence_frames: list[QPixmap] = []
        self._sequence_index = 0
        self._sequence_timer = QTimer(self)
        self._sequence_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._sequence_timer.setInterval(max(1, int(frame_interval_ms)))
        self._sequence_timer.timeout.connect(self._advance_sequence)
        self.setFixedSize(self._display_width, self._size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Animated assets are transparent overlays.  An explicit transparent
        # surface prevents global QLabel/theme rules from drawing a dark tile
        # behind APNG frame sequences (most visible on selected sidebar rows).
        self.setStyleSheet("background: transparent; border: 0;")
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            mouse_transparent,
        )
        self._load()
        if self._autoplay:
            QTimer.singleShot(0, self._start_animation)

    def attach_hover_source(self, widget) -> None:
        """Animate from the owning control without consuming its mouse events."""
        widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        # Queued hover events may outlive a catalog row rebuilt during tests or
        # rapid navigation. Never cross into the C++ base through a deleted
        # QLabel wrapper.
        if not isValid(self) or watched is None or not isValid(watched):
            return False
        if self._autoplay:
            return False
        if event.type() == QEvent.Type.Enter:
            if not hasattr(watched, "isEnabled") or watched.isEnabled():
                self._start_animation()
        elif event.type() == QEvent.Type.Leave:
            self._stop_animation()
        return False

    def _load(self) -> None:
        path = IconRegistry.path(self._key, category=self._key.partition(".")[0])
        if path is None:
            self.clear()
            return
        movie = QMovie(str(path))
        movie.setScaledSize(QSize(self._display_width, self._size))
        if not movie.isValid():
            IconRegistry._warn_once(f"movie:{path}", "Invalid animated icon: %s", path)
            self.clear()
            return
        self._movie = movie
        sequence_dir = path.with_name(f"{path.stem}_frames")
        if sequence_dir.is_dir():
            self._sequence_frames = [
                QPixmap(str(frame_path)).scaled(
                    self._display_width,
                    self._size,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                for frame_path in sorted(sequence_dir.glob("frame_*.png"))
            ]
        if self._idle_key:
            self._show_idle()
        else:
            self.setMovie(movie)
            movie.jumpToFrame(self._idle_frame)

    def _show_idle(self) -> None:
        if self._idle_key:
            self.setPixmap(
                IconRegistry.pixmap(
                    self._idle_key,
                    self._size,
                    variant="original",
                    category="service",
                )
            )

    def enterEvent(self, event) -> None:
        if not self._autoplay:
            self._start_animation()
        super().enterEvent(event)

    def _start_animation(self) -> None:
        if not isValid(self) or reduced_motion_enabled():
            return
        if self._sequence_frames:
            self._sequence_index = 0
            self.setPixmap(self._sequence_frames[0])
            self._sequence_timer.start()
            return
        if self._movie is not None:
            self.setMovie(self._movie)
            if self._idle_key:
                self._movie.jumpToFrame(0)
            self._movie.start()

    def _advance_sequence(self) -> None:
        if not isValid(self) or not self._sequence_frames:
            return
        self._sequence_index = (self._sequence_index + 1) % len(
            self._sequence_frames
        )
        self.setPixmap(self._sequence_frames[self._sequence_index])

    def leaveEvent(self, event) -> None:
        if not self._autoplay:
            self._stop_animation()
        super().leaveEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._autoplay:
            self._start_animation()

    def _stop_animation(self) -> None:
        self._sequence_timer.stop()
        if self._movie is not None:
            self._movie.stop()
            if self._idle_key:
                self._show_idle()
            else:
                self._movie.jumpToFrame(self._idle_frame)

    def hideEvent(self, event) -> None:
        self._sequence_timer.stop()
        if self._movie is not None:
            self._movie.stop()
        super().hideEvent(event)
