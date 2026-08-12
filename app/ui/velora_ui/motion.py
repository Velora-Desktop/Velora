"""Small presentation-only motion primitives shared by Velora widgets."""
from __future__ import annotations

import os

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize

from app.ui.velora_ui.theme.tokens import Motion
from app.ui.velora_ui.icons import IconProvider


def reduced_motion_enabled() -> bool:
    return os.getenv("VELORA_REDUCED_MOTION", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def apply_favorite_icon(
    button, selected: bool, *, size: int = 20,
    active_color: str = "#FFC52E", idle_color: str = "#B8C0C8",
) -> None:
    """Render the shared filled/outline favorite star without changing geometry."""
    button.setIcon(IconProvider.icon(
        "rating.star_filled" if selected else "rating.star_outline",
        size,
        active_color if selected else idle_color,
    ))
    if button.iconSize().isEmpty():
        button.setIconSize(QSize(size, size))


def animate_icon_pulse(
    button, *, adding: bool, state_change: Callable[[], None] | None = None,
) -> QPropertyAnimation | None:
    """Pulse only iconSize; the button and surrounding layout never move."""
    if reduced_motion_enabled():
        if state_change is not None:
            state_change()
        return None
    base = button.iconSize()
    if base.isEmpty():
        base = QSize(20, 20)
    # Adding and removing use the same outward pulse. At the peak the star
    # switches between yellow fill and neutral outline, then returns to base.
    factor = Motion.FAVORITE_ADD_SCALE
    peak = QSize(max(1, round(base.width() * factor)), max(1, round(base.height() * factor)))
    animation = QPropertyAnimation(button, b"iconSize", button)
    animation.setDuration(Motion.FAVORITE_DURATION)
    animation.setStartValue(base)
    animation.setKeyValueAt(0.38, peak)
    animation.setKeyValueAt(0.62, peak)
    animation.setEndValue(base)
    animation.setEasingCurve(QEasingCurve.Type.InOutSine)
    if state_change is not None:
        state_changed = False

        def apply_state_at_peak(_value=None) -> None:
            nonlocal state_changed
            if not state_changed and animation.currentTime() >= animation.duration() * 0.46:
                state_changed = True
                state_change()

        animation.valueChanged.connect(apply_state_at_peak)
        animation.finished.connect(apply_state_at_peak)
    animation.start()
    return animation
