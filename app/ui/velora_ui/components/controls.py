"""Shared selectors whose values are stable identifiers, never display text."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget,
)

from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.moods import MoodRegistry
from app.ui.rating_palette import rating_color
from app.ui.velora_ui.theme.tokens import (
    Colors, Dimensions, Radii, Spacing,
)


class VeloraScrollArrow(QPushButton):
    """Reusable hold-to-scroll arrow with a stable disabled-edge state."""

    step_requested = Signal()

    def __init__(self, direction: str, parent=None) -> None:
        super().__init__(parent)
        if direction not in {"left", "right"}:
            raise ValueError("direction must be left or right")
        self.setObjectName("veloraScrollArrow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(320)
        self.setAutoRepeatInterval(75)
        self.setIcon(IconProvider.icon(
            f"navigation.arrow_{direction}",
            Dimensions.ICON_SMALL,
            Colors.TEXT_SECONDARY,
        ))
        self.clicked.connect(self.step_requested.emit)
        self.setStyleSheet(
            f"QPushButton#veloraScrollArrow{{background:{Colors.SURFACE_CARD};"
            f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:{Radii.MEDIUM}px;}}"
            f"QPushButton#veloraScrollArrow:hover{{background:{Colors.BACKGROUND_SELECTED};"
            f"border-color:{Colors.BORDER_HOVER};}}"
            f"QPushButton#veloraScrollArrow:disabled{{background:{Colors.SURFACE_DISABLED};"
            f"border-color:{Colors.BORDER_SUBTLE};}}"
        )


class VeloraRatingSelector(QWidget):
    """Compact 1–10 selector shared by Journey editors."""

    rating_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value: float | None = None
        self._buttons: list[QPushButton] = []
        layout = QHBoxLayout(self)
        self.setFixedHeight(72)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(Spacing.SPACE_4)
        button_size = 60
        self.setFixedWidth(10 * button_size + 9 * Spacing.SPACE_4)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        for number in range(1, 11):
            button = QPushButton(str(number))
            color = rating_color(float(number))
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(button_size, button_size)
            button.setStyleSheet(
                f"QPushButton{{background:{Colors.SURFACE_CARD};color:{color};"
                f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:5px;"
                "font-size:20px;font-weight:700;padding:0;}"
                f"QPushButton:hover{{background:{Colors.BACKGROUND_HOVER};"
                f"border-color:{color};}}"
                f"QPushButton:checked{{background:{Colors.BACKGROUND_SELECTED};"
                f"border:2px solid {color};color:{color};}}"
            )
            button.clicked.connect(
                lambda checked=False, value=number: self.setValue(float(value))
            )
            self._buttons.append(button)
            layout.addWidget(button)

    def setValue(self, value: float | None) -> None:
        numeric = float(value or 0)
        self._value = numeric if numeric > 0 else None
        selected = round(numeric) if self._value is not None else None
        for index, button in enumerate(self._buttons, 1):
            button.setChecked(index == selected)
        self.rating_changed.emit(self._value)

    def value(self) -> float | None:
        return self._value

    def clear(self) -> None:
        self.setValue(None)


class VeloraMoodSelector(QWidget):
    moodChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mood_id: str | None = None
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.setMinimumWidth(
            len(MoodRegistry.all()) * 36
            + (len(MoodRegistry.all()) - 1) * Spacing.SPACE_6
        )
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(Spacing.SPACE_6)
        for mood in MoodRegistry.all():
            button = QPushButton()
            button.setCheckable(True)
            button.setFixedSize(36, 36)
            button.setIcon(IconProvider.icon(
                mood.icon_key, Dimensions.ICON_LARGE, mood.color
            ))
            button.setIconSize(QSize(Dimensions.ICON_LARGE, Dimensions.ICON_LARGE))
            button.setToolTip(f"{mood.display_name}\n{mood.tooltip}")
            button.setStyleSheet(
                f"QPushButton{{background:{Colors.SURFACE_CARD};"
                f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:{Radii.MEDIUM}px;}}"
                f"QPushButton:hover{{background:{Colors.BACKGROUND_HOVER};"
                f"border-color:{mood.color};}}"
                f"QPushButton:checked{{background:{Colors.BACKGROUND_SELECTED};"
                f"border:2px solid {mood.color};}}"
            )
            button.clicked.connect(
                lambda checked=False, mood_id=mood.id: self.set_mood_id(
                    mood_id if checked else None
                )
            )
            self._buttons[mood.id] = button
            self._group.addButton(button)
            layout.addWidget(button)
        layout.addStretch()

    def mood_id(self) -> str | None:
        return self._mood_id

    def set_mood_id(self, mood_id: str | None) -> None:
        if mood_id is not None:
            MoodRegistry.require(mood_id)
        self._mood_id = mood_id
        for key, button in self._buttons.items():
            button.blockSignals(True)
            button.setChecked(key == mood_id)
            button.blockSignals(False)
        self.moodChanged.emit(mood_id)

    def currentText(self) -> str:
        mood = MoodRegistry.get(self._mood_id)
        return mood.display_name if mood else "Без настроения"
