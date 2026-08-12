"""Shared semantic colour scale for numeric ratings in Velora UI."""
from __future__ import annotations

from PySide6.QtGui import QColor


MISSING_RATING_COLOR = "#8A929A"


def rating_color(value: object) -> str:
    """Return a continuous red -> yellow -> green colour for a 0..10 score."""
    try:
        score = max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return MISSING_RATING_COLOR

    if score <= 5.0:
        start, end, position = QColor("#FF4545"), QColor("#FFC52E"), score / 5.0
    else:
        start, end, position = QColor("#FFC52E"), QColor("#20D874"), (score - 5.0) / 5.0
    red = round(start.red() + (end.red() - start.red()) * position)
    green = round(start.green() + (end.green() - start.green()) * position)
    blue = round(start.blue() + (end.blue() - start.blue()) * position)
    return QColor(red, green, blue).name().upper()


RatingColorPolicy = rating_color
