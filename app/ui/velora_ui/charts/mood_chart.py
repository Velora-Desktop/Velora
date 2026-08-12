"""Reusable High-DPI Journey mood/rating chart."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from app.ui.velora_ui.moods import MoodRegistry
from app.ui.velora_ui.theme.tokens import Colors
from app.ui.rating_palette import rating_color


@dataclass(frozen=True, slots=True)
class MoodChartPoint:
    stage_number: int
    mood_id: str | None = None
    rating: float | None = None
    selected: bool = False
    label: str | None = None
    is_event: bool = False


class MoodChart(QWidget):
    TREND_EPSILON = 0.25

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._points: tuple[MoodChartPoint, ...] = ()
        self.setMinimumHeight(130)
        self.setMaximumHeight(165)
        self.setMouseTracking(True)

    def set_points(self, points: Iterable[MoodChartPoint]) -> None:
        validated = []
        for point in points:
            if point.mood_id is not None:
                MoodRegistry.require(point.mood_id)
            validated.append(point)
        self._points = tuple(validated)
        self.update()

    @property
    def points(self) -> tuple[MoodChartPoint, ...]:
        return self._points

    @classmethod
    def trend_color(cls, previous: MoodChartPoint, current: MoodChartPoint) -> str:
        """Return the semantic color of one rating transition."""
        if previous.rating is None or current.rating is None:
            return Colors.TEXT_DISABLED
        delta = current.rating - previous.rating
        if delta > cls.TREND_EPSILON:
            return Colors.SUCCESS
        if delta < -cls.TREND_EPSILON:
            return Colors.DANGER
        return Colors.ACCENT_PRIMARY

    @staticmethod
    def rating_position(point: MoodChartPoint) -> float:
        """Map a rating to the chart; unrated points stay on the zero line."""
        if point.rating is None:
            return 0.0
        return (max(1.0, min(10.0, point.rating)) - 1.0) / 9.0

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin, baseline = 18, self.height() - 36
        width = max(1, self.width() - margin * 2)
        step = width / max(1, len(self._points) - 1)
        rendered = []
        for index, point in enumerate(self._points):
            mood = MoodRegistry.get(point.mood_id)
            normalized = self.rating_position(point)
            rendered.append((
                margin + index * step,
                baseline - normalized * (self.height() - 52),
                point,
                mood,
            ))
        for previous, current in zip(rendered, rendered[1:]):
            path = QPainterPath()
            path.moveTo(previous[0], previous[1])
            path.lineTo(current[0], current[1])
            painter.setPen(QPen(QColor(
                self.trend_color(previous[2], current[2])
            ), 2))
            painter.drawPath(path)
        for x, y, point, mood in rendered:
            color = (
                rating_color(point.rating) if point.rating is not None
                else Colors.TEXT_DISABLED
            )
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor(Colors.TEXT_PRIMARY), 1) if point.selected else Qt.PenStyle.NoPen)
            radius = 5 if point.selected else 3 if point.is_event else 4
            painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)
            if not point.is_event:
                painter.setPen(QPen(QColor(Colors.BORDER_SUBTLE), 1))
                painter.drawLine(int(x), baseline + 6, int(x), baseline + 10)
                painter.setPen(QColor(Colors.TEXT_MUTED))
                painter.drawText(
                    QRectF(x - 18, baseline + 10, 36, 20),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    point.label or f"{point.stage_number:02d}",
                )

    def mouseMoveEvent(self, event) -> None:
        if not self._points:
            return super().mouseMoveEvent(event)
        margin = 18
        width = max(1, self.width() - margin * 2)
        step = width / max(1, len(self._points) - 1)
        nearest = min(
            range(len(self._points)),
            key=lambda index: abs(event.position().x() - (margin + index * step)),
        )
        point = self._points[nearest]
        if abs(event.position().x() - (margin + nearest * step)) <= 14:
            mood = MoodRegistry.get(point.mood_id)
            rating = "—" if point.rating is None else f"{point.rating:.1f}"
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"Этап {point.stage_number:02d}\n"
                f"Настроение: {mood.display_name if mood else 'не выбрано'}\n"
                f"Оценка: {rating}",
                self,
            )
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)
