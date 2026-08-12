"""Stable semantic icon API with cached, non-failing fallback rendering."""
from __future__ import annotations

import logging
from functools import lru_cache

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap

from app.core.icon_registry import IconRegistry

LOGGER = logging.getLogger(__name__)

_KEYS = {
    "common.add": ("add", None),
    "common.more": ("more", "ui"),
    "common.delete": ("delete", "ui"),
    "common.save": ("save", None),
    "common.exit": ("metadata.external_link", "metadata"),
    "navigation.arrow_left": ("chevron_left", "ui"),
    "navigation.arrow_right": ("chevron_right", "ui"),
    "navigation.chevron_down": ("chevron_down", "ui"),
    "journey.note": ("journey-note", "journey"),
    "journey.impression": ("journey-impression", "journey"),
    "journey.screenshot": ("journey-screenshot", "journey"),
    "journey.achievement": ("journey-achievement", "journey"),
    "journey.favorite": ("journey-favorite", "journey"),
    "journey.music": ("journey-music", "journey"),
    "journey.difficult": ("journey-difficult", "journey"),
    "journey.rating_change": ("journey-rating", "journey"),
    "journey.other": ("journey-other", "journey"),
    "status.completed": ("status-completed", "journey"),
    "status.current": ("status-current", "journey"),
    "status.in_progress": ("status-progress", "journey"),
    "status.not_started": ("status-not-started", "journey"),
    "rating.star_filled": ("favorite", "media_types"),
    "rating.star_outline": ("favorite", "media_types"),
    "mood.excited": ("mood-excited", "journey"),
    "mood.happy": ("mood-happy", "journey"),
    "mood.positive": ("mood-positive", "journey"),
    "mood.neutral": ("mood-neutral", "journey"),
    "mood.tired": ("mood-tired", "journey"),
    "mood.bored": ("mood-bored", "journey"),
    "mood.disappointed": ("mood-disappointed", "journey"),
    "mood.angry": ("mood-angry", "journey"),
    "service.boosty.dark": ("service.boosty.dark", "service"),
    "service.boosty.light": ("service.boosty.light", "service"),
    "service.boosty.color": ("service.boosty.color", "service"),
    "genre.rpg": ("genre.rpg", "genre"),
    "genre.action": ("genre.action", "genre"),
    "genre.racing": ("genre.racing", "genre"),
    "genre.strategy": ("genre.strategy", "genre"),
    "genre.adventure": ("genre.adventure", "genre"),
    "genre.fighting": ("genre.action", "genre"),
    "genre.drama": ("genre.drama", "genre"),
    "genre.comedy": ("genre.comedy", "genre"),
    "genre.fantasy": ("genre.fantasy", "genre"),
    "genre.system": ("metadata.system", "metadata"),
    "genre.graphics": ("metadata.graphics", "metadata"),
    "metadata.external_link": ("metadata.external_link", "metadata"),
    "metadata.system": ("metadata.system", "metadata"),
    "metadata.engine": ("metadata.engine", "metadata"),
    "metadata.dlc": ("metadata.dlc", "metadata"),
    "metadata.release": ("metadata.release", "metadata"),
    "metadata.game_support": ("metadata.game_support", "metadata"),
    "metadata.players": ("metadata.players", "metadata"),
    "metadata.graphics": ("metadata.graphics", "metadata"),
    "service.netflix": ("service.netflix", "service"),
    "service.netflix.idle": ("service.netflix.idle", "service"),
    "service.amediateka": ("service.amediateka", "service"),
    "service.kinopoisk": ("service.kinopoisk", "service"),
    "service.premier": ("service.premier", "service"),
    "animated.budget": ("animated.budget", "animated"),
    "animated.search": ("animated.search", "animated"),
    "animated.settings": ("animated.settings", "animated"),
    "animated.navigation_arrow_right": ("animated.navigation_arrow_right", "animated"),
    "animated.navigation_arrow_left": ("animated.navigation_arrow_left", "animated"),
    "animated.user_avatar": ("animated.user_avatar", "animated"),
    "animated.language_flag": ("animated.language_flag", "animated"),
    "animated.genre_comedy": ("animated.genre_comedy", "animated"),
    "animated.developer": ("animated.developer", "animated"),
    "animated.plus": ("animated.plus", "animated"),
    "animated.cinema": ("animated.cinema", "animated"),
    "animated.info": ("animated.info", "animated"),
    "animated.genre_animation": ("animated.genre_animation", "animated"),
    "animated.exit": ("animated.exit", "animated"),
    "animated.platform": ("animated.platform", "animated"),
    "animated.ticket": ("animated.ticket", "animated"),
}

_ORIGINAL_KEYS = {
    "service.boosty.dark", "service.boosty.light", "service.boosty.color",
    "service.netflix", "service.netflix.idle", "service.amediateka",
    "service.premier", "animated.budget", "animated.search", "animated.settings",
    "animated.navigation_arrow_right", "animated.navigation_arrow_left",
    "animated.user_avatar",
    "animated.language_flag",
    "animated.genre_comedy",
    "animated.developer",
    "animated.plus",
    "animated.cinema",
    "animated.info",
    "animated.genre_animation",
    "animated.exit",
    "animated.platform",
    "animated.ticket",
}


class IconProvider:
    @classmethod
    def exists(cls, key: str) -> bool:
        target = _KEYS.get(key)
        return bool(target and IconRegistry.path(target[0], category=target[1]))

    @classmethod
    @lru_cache(maxsize=256)
    def icon(cls, key: str, size: int = 20, color: str | None = None) -> QIcon:
        pixmap = cls.pixmap(key, size=size, color=color)
        return QIcon(pixmap)

    @classmethod
    @lru_cache(maxsize=512)
    def pixmap(cls, key: str, size: int = 20, color: str | None = None) -> QPixmap:
        target = _KEYS.get(key)
        if target:
            if key in _ORIGINAL_KEYS and not color:
                pixmap = IconRegistry.pixmap(
                    target[0], size, variant="original", category=target[1]
                )
            else:
                pixmap = (
                    IconRegistry.tinted_pixmap(target[0], size, color, category=target[1])
                    if color else IconRegistry.pixmap(target[0], size, category=target[1])
                )
            if not pixmap.isNull():
                pixmap.setDevicePixelRatio(1.0)
                return pixmap
        IconRegistry._warn_once(f"provider:{key}", "Unknown or missing Velora icon: %s", key)
        fallback = QPixmap(QSize(size, size))
        fallback.fill(0)
        return fallback

    @staticmethod
    def keys() -> tuple[str, ...]:
        return tuple(_KEYS)
