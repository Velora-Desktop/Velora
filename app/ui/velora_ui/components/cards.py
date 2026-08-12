"""Reusable, presentation-only cards used by Journey and future modules."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.moods import MoodRegistry
from app.ui.velora_ui.theme.tokens import Colors, Dimensions, Radii, Spacing, Typography
from app.ui.rating_palette import rating_color
from app.ui.velora_ui.motion import animate_icon_pulse


class VeloraCard(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._selected = False
        self.setProperty("selected", False)
        self.setObjectName("veloraCard")
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"QFrame#veloraCard{{background:{Colors.SURFACE_CARD};"
            f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:{Radii.CARD}px;}}"
            f"QFrame#veloraCard:hover{{background:{Colors.SURFACE_CARD_HOVER};"
            f"border-color:{Colors.BORDER_HOVER};}}"
            f"QFrame#veloraCard[selected=\"true\"]{{background:{Colors.BACKGROUND_SELECTED};"
            f"border-color:{Colors.BORDER_ACTIVE};}}"
        )


class VeloraStageCard(QFrame):
    stage_selected = Signal(str)
    stage_open_requested = Signal(str)
    status_toggled = Signal(str, bool)
    favorite_toggled = Signal(str, bool)

    _status = {
        "complete": ("Завершено", Colors.STATUS_COMPLETED, "status.completed"),
        "active": ("Текущая", Colors.STATUS_CURRENT, "status.current"),
        "progress": ("В процессе", Colors.STATUS_IN_PROGRESS, "status.in_progress"),
        "abandoned": ("Брошено", Colors.STATUS_ABANDONED, "status.in_progress"),
        "future": ("Не начато", Colors.STATUS_NOT_STARTED, "status.not_started"),
    }

    def __init__(
        self,
        stage_id: str,
        stage_number: int,
        title: str,
        status: str,
        duration: str = "—",
        rating: float | None = None,
        has_favorite: bool = False,
        has_events: bool = False,
        event_count: int = 0,
        mood_id: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.stage_id = stage_id
        self._status_id = status
        self._checked = False
        self._favorite = bool(has_favorite)
        self._favorite_animation = None
        self.setObjectName("veloraStageCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(
            Dimensions.JOURNEY_COMPACT_STAGE_WIDTH,
            Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT,
        )
        self.setToolTip(title)
        label, color, icon_key = self._status.get(status, self._status["future"])
        root = QVBoxLayout(self)
        root.setContentsMargins(
            Spacing.SPACE_16, Spacing.SPACE_12,
            Spacing.SPACE_16, Spacing.SPACE_12,
        )
        root.setSpacing(Spacing.SPACE_4)
        top = QHBoxLayout()
        self.status_icon = QPushButton()
        self.status_icon.setObjectName("stageStatusButton")
        self.status_icon.setFixedSize(24, 24)
        self.status_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_icon.setToolTip("Переключить: текущее / завершено")
        self.status_icon.setStyleSheet(
            "QPushButton#stageStatusButton{background:transparent;border:0;padding:2px;}"
            f"QPushButton#stageStatusButton:hover{{background:{Colors.ACCENT_SUBTLE};"
            f"border:1px solid {Colors.BORDER_HOVER};border-radius:11px;}}"
        )
        self.status_icon.setIcon(IconProvider.icon(
            icon_key, Dimensions.ICON_MEDIUM, color
        ))
        self.status_icon.setIconSize(QSize(
            Dimensions.ICON_MEDIUM, Dimensions.ICON_MEDIUM
        ))
        self.status_icon.clicked.connect(self._request_completion)
        number = QLabel(f"{stage_number:02d}")
        number.setStyleSheet(
            f"color:{Colors.TEXT_PRIMARY};{Typography.JOURNEY_STAGE_NUMBER}border:0;"
        )
        top.addWidget(self.status_icon)
        top.addWidget(number)
        top.addStretch()
        self.favorite_button = QPushButton()
        self.favorite_button.setObjectName("stageFavoriteButton")
        self.favorite_button.setFixedSize(30, 30)
        self.favorite_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favorite_button.setStyleSheet(
            "QPushButton#stageFavoriteButton{background:transparent;border:0;padding:2px;}"
            f"QPushButton#stageFavoriteButton:hover{{background:{Colors.ACCENT_SUBTLE};"
            f"border:1px solid {Colors.BORDER_HOVER};border-radius:11px;}}"
        )
        self._render_favorite()
        self.favorite_button.clicked.connect(self._toggle_favorite)
        top.addWidget(self.favorite_button)
        root.addLayout(top)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(38)
        title_label.setStyleSheet(
            f"color:{Colors.TEXT_PRIMARY};{Typography.JOURNEY_STAGE_TITLE}border:0;"
        )
        root.addWidget(title_label, 1)
        self.status_label = QLabel(label)
        self.status_label.setStyleSheet(
            f"color:{color};{Typography.JOURNEY_STAGE_STATUS}border:0;"
        )
        root.addWidget(self.status_label)
        self.event_count_label = QLabel(f"Событий: {max(0, int(event_count))}")
        self.event_count_label.setStyleSheet(
            f"color:{Colors.TEXT_MUTED};{Typography.JOURNEY_STAGE_META}border:0;"
        )
        root.addWidget(self.event_count_label)
        bottom = QHBoxLayout()
        duration_label = QLabel(duration)
        duration_label.setVisible(bool(duration and duration != "—"))
        duration_label.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};{Typography.BODY_SECONDARY}border:0;")
        rating_label = QLabel("—" if rating is None else f"{rating:.1f}")
        rating_label.setVisible(rating is not None)
        rating_label.setStyleSheet(
            f"color:{rating_color(rating) if rating is not None else Colors.TEXT_MUTED};"
            f"{Typography.JOURNEY_STAGE_META}border:0;"
        )
        bottom.addWidget(duration_label)
        bottom.addStretch()
        bottom.addWidget(rating_label)
        mood = MoodRegistry.get(mood_id)
        if mood is not None:
            mood_icon = QLabel()
            mood_icon.setPixmap(IconProvider.pixmap(
                mood.icon_key, Dimensions.ICON_SMALL, mood.color
            ))
            mood_icon.setToolTip(mood.tooltip)
            bottom.addWidget(mood_icon)
        root.addLayout(bottom)
        # Text and decorative icons must not become separate mouse targets.
        # Otherwise a real double-click on the title/status is swallowed by a
        # child QLabel and never reaches the stage card.
        for label_widget in self.findChildren(QLabel):
            label_widget.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._checked = bool(selected)
        self.setProperty("selected", self._checked)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.stage_selected.emit(self.stage_id)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.stage_selected.emit(self.stage_id)
            self.stage_open_requested.emit(self.stage_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _toggle_favorite(self) -> None:
        self._favorite = not self._favorite
        if self._favorite_animation is not None:
            self._favorite_animation.stop()
        self._favorite_animation = animate_icon_pulse(
            self.favorite_button,
            adding=self._favorite,
            state_change=self._render_favorite,
        )
        self.favorite_toggled.emit(self.stage_id, self._favorite)

    def _request_completion(self) -> None:
        """Toggle the mission's primary state without rebuilding the card."""
        completed = self._status_id not in ("complete", "completed")
        self.status_toggled.emit(self.stage_id, completed)

    def _render_favorite(self) -> None:
        self.favorite_button.setIcon(IconProvider.icon(
            "rating.star_filled" if self._favorite else "rating.star_outline",
            Dimensions.ICON_MEDIUM,
            Colors.WARNING if self._favorite else Colors.TEXT_MUTED,
        ))
        if self.favorite_button.iconSize().isEmpty():
            self.favorite_button.setIconSize(QSize(
                Dimensions.ICON_MEDIUM, Dimensions.ICON_MEDIUM
            ))

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.stage_selected.emit(self.stage_id)
            event.accept()
            return
        super().keyPressEvent(event)

    def _apply_style(self) -> None:
        color = self._status.get(self._status_id, self._status["future"])[1]
        self.setStyleSheet(
            f"QFrame#veloraStageCard{{background:{Colors.SURFACE_CARD};"
            f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:{Radii.CARD}px;"
            f"color:{Colors.TEXT_PRIMARY};}}"
            f"QFrame#veloraStageCard:hover{{background:{Colors.SURFACE_CARD_HOVER};"
            f"border-color:{Colors.BORDER_HOVER};}}"
            f"QFrame#veloraStageCard[selected=\"true\"]{{background:{Colors.BACKGROUND_SELECTED};"
            f"border-color:{Colors.BORDER_ACTIVE};color:{Colors.TEXT_ON_ACCENT};}}"
            f"QFrame#veloraStageCard:focus{{border-color:{Colors.BORDER_ACTIVE};}}"
            f"QFrame#veloraStageCard:disabled{{background:{Colors.SURFACE_DISABLED};"
            f"color:{Colors.TEXT_DISABLED};border-color:{Colors.BORDER_SUBTLE};}}"
        )
        self.setProperty("statusColor", color)


class VeloraActionCard(QFrame):
    activated = Signal(str, str)

    def __init__(self, action_id: str, icon_key: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self.action_id = action_id
        self.text = text
        self.setObjectName("veloraActionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(
            Dimensions.JOURNEY_ACTION_CARD_WIDTH,
            Dimensions.JOURNEY_ACTION_CARD_HEIGHT,
        )
        self.setStyleSheet(
            f"QFrame#veloraActionCard{{background:{Colors.SURFACE_CARD};"
            f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:{Radii.MEDIUM}px;}}"
            f"QFrame#veloraActionCard:hover,QFrame#veloraActionCard:focus{{"
            f"background:{Colors.BACKGROUND_SELECTED};border-color:{Colors.BORDER_HOVER};}}"
            f"QFrame#veloraActionCard:disabled{{background:{Colors.SURFACE_DISABLED};"
            f"border-color:{Colors.BORDER_SUBTLE};}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SPACE_6, Spacing.SPACE_6, Spacing.SPACE_6, Spacing.SPACE_6)
        layout.setSpacing(Spacing.SPACE_2)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(IconProvider.pixmap(
            icon_key, Dimensions.ICON_MEDIUM, Colors.ACCENT_PRIMARY
        ))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumHeight(30)
        self.text_label.setStyleSheet(
            f"color:{Colors.TEXT_SECONDARY};border:0;{Typography.CAPTION}"
        )
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def mouseReleaseEvent(self, event) -> None:
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.activated.emit(self.action_id, self.text)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.action_id, self.text)
            event.accept()
            return
        super().keyPressEvent(event)


class VeloraEventCard(QFrame):
    """Compact event presentation shared by Journey timelines and diaries."""

    def __init__(
        self,
        icon_key: str,
        event_type: str,
        title: str,
        *,
        subtitle: str = "",
        tooltip: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("veloraEventCard")
        self.setFixedHeight(80)
        self.setToolTip(tooltip or title)
        self.setStyleSheet("QFrame#veloraEventCard{background:transparent;border:0;}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        icon = QLabel()
        icon.setFixedSize(Dimensions.ICON_MEDIUM, Dimensions.ICON_MEDIUM)
        icon.setPixmap(IconProvider.pixmap(
            icon_key, Dimensions.ICON_MEDIUM, Colors.ACCENT_PRIMARY
        ))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kind = QLabel(event_type)
        kind.setFixedHeight(16)
        kind.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kind.setToolTip(event_type)
        kind.setStyleSheet(
            f"color:{Colors.TEXT_MUTED};{Typography.CAPTION}border:0;"
        )
        text = QLabel(title)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(False)
        text.setFixedHeight(18 if title else 0)
        text.setVisible(bool(title))
        text.setToolTip(title)
        text.setStyleSheet(
            f"color:{Colors.TEXT_PRIMARY};{Typography.BODY_SECONDARY}"
            "font-weight:600;border:0;"
        )
        description = QLabel(subtitle)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(False)
        description.setFixedHeight(18 if subtitle else 0)
        description.setVisible(bool(subtitle))
        description.setToolTip(subtitle)
        description.setStyleSheet(
            f"color:{Colors.TEXT_PRIMARY};{Typography.CAPTION}border:0;"
        )
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(kind)
        layout.addWidget(text)
        layout.addWidget(description)
        self.kind_label = kind
        self.title_label = text
        self.description_label = description
