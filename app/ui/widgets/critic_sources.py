from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.core.icon_registry import IconRegistry


SOURCE_ICON_IDS = {
    "Metacritic": "source_metacritic",
    "IGN": "source_ign",
    "PC Gamer": "source_pc_gamer",
    "GameSpot": "source_gamespot",
    "DualShockers": "source_dualshockers",
    "IMDb": "source_imdb",
    "Кинопоиск": "source_kinopoisk",
    "Кинопоиск": "source_kinopoisk",
    "Rotten Tomatoes": "source_rotten_tomatoes",
    "Letterboxd": "source_letterboxd",
    "PCMag": "source_pcmag",
    "TechRadar": "source_techradar",
    "CNET": "source_cnet",
    "Tom's Guide": "source_toms_guide",
}

SOURCE_BRAND_COLORS = {
    "Metacritic": "#FFCC34",
    "IGN": "#BF1313",
    "PC Gamer": "#D71920",
    "GameSpot": "#FFB000",
    "DualShockers": "#4DA3FF",
    "IMDb": "#F5C518",
    "Кинопоиск": "#FF5500",
    "Кинопоиск": "#FF5500",
    "Rotten Tomatoes": "#FA320A",
    "Letterboxd": "#00E054",
    "PCMag": "#E1262F",
    "TechRadar": "#20C997",
    "CNET": "#E71D1D",
    "Tom's Guide": "#2774AE",
}

SOURCE_SETS = {
    "Игры": ("Metacritic", "IGN", "DualShockers", "PC Gamer"),
    "Фильмы": ("IMDb", "Кинопоиск", "Rotten Tomatoes", "Metacritic"),
    "Сериалы": ("IMDb", "Кинопоиск", "Rotten Tomatoes", "Metacritic"),
    "Программы": ("PCMag", "TechRadar", "CNET", "Tom's Guide"),
}


def source_slots(
    media_type: str,
    scores: dict[str, float | None],
    primary_source: str = "",
    limit: int = 4,
) -> list[tuple[str, float | None]]:
    """Return critic cards in the catalog-defined order without a lead source."""
    if not any(value is not None for value in scores.values()):
        return []
    configured = list(SOURCE_SETS.get(media_type, ()))
    # Keys describe the four configured slots; a slot may intentionally have
    # no score yet and must still keep its position.
    available = list(scores)
    ordered: list[str] = []
    for name in (*available, *configured):
        if name and name not in ordered:
            ordered.append(name)
    return [(name, scores.get(name)) for name in ordered[:limit]]


def source_icon_id(source: str) -> str:
    return SOURCE_ICON_IDS.get(source, "source_press")


def source_brand_color(source: str) -> str:
    """Return one consistent brand color for the source card and its score."""
    return SOURCE_BRAND_COLORS.get(source, "#AAB7C2")


def apply_source_logo(label: QLabel, source: str, size: QSize = QSize(36, 24)) -> None:
    label.setText("")
    label.setPixmap(
        IconRegistry.pixmap(
            source_icon_id(source),
            size.width(),
            size.height(),
            variant="color",
            category="ratings",
        )
    )
    label.setFixedSize(size)
    label.setToolTip(source)


class CriticSourceStrip(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def set_sources(self, sources: list[str], primary_source: str = "") -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        caption = QLabel("На основе:")
        caption.setObjectName("muted")
        self._layout.addWidget(caption)
        if not sources:
            empty = QLabel("источники не указаны")
            empty.setObjectName("muted")
            self._layout.addWidget(empty)
        for source in sources[:5]:
            logo = QLabel()
            apply_source_logo(logo, source, QSize(24, 18))
            self._layout.addWidget(logo)
            name = QLabel(source)
            name.setObjectName("muted")
            self._layout.addWidget(name)
        self._layout.addStretch(1)
