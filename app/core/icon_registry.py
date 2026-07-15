from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QStyle


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ICON_ROOT = PROJECT_ROOT / "assets" / "icons"


class IconRegistry:
    """Single, cached access point for every application icon."""

    _entries: dict[str, list[dict]] | None = None
    _standard_ids = {"back", "forward", "add", "delete", "refresh", "save"}

    @classmethod
    def _load(cls) -> dict[str, list[dict]]:
        if cls._entries is not None:
            return cls._entries
        cls._entries = {}
        manifest = ICON_ROOT / "manifest.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for entry in data.get("icons", []):
                cls._entries.setdefault(entry["id"], []).append(entry)
        except (OSError, ValueError, KeyError) as exc:
            LOGGER.warning("Icon manifest could not be loaded: %s", exc)
        return cls._entries

    @classmethod
    def path(
        cls,
        icon_id: str,
        *,
        variant: str = "auto",
        category: str | None = None,
    ) -> Path | None:
        entries = cls._load().get(icon_id, [])
        if category:
            entries = [entry for entry in entries if entry.get("category") == category]
        entry = cls._select(entries, variant)
        if not entry:
            legacy = cls._legacy_path(icon_id, category)
            if legacy or icon_id in cls._standard_ids:
                return legacy
            LOGGER.warning("Unknown icon id: %s (%s/%s)", icon_id, category, variant)
            return None
        relative = cls._normalized_relative(entry, variant)
        path = ICON_ROOT / relative
        if path.is_file():
            return path
        LOGGER.warning("Missing icon file: %s", path)
        return cls._legacy_path(icon_id, category)

    @staticmethod
    def _select(entries: list[dict], variant: str) -> dict | None:
        if not entries:
            return None
        if variant == "svg":
            return next((item for item in entries if item.get("format") == "svg"), None)
        if variant == "dark":
            return next((item for item in entries if item.get("format") == "svg"), next((item for item in entries if item.get("format") == "png"), None))
        if variant == "color":
            return next((item for item in entries if item.get("format") == "png"), None)
        return next((item for item in entries if item.get("format") == "svg"), entries[0])

    @staticmethod
    def _normalized_relative(entry: dict, variant: str) -> Path:
        source = entry.get("path", "")
        if entry.get("format") == "png":
            if variant in {"auto", "dark"} and entry.get("dark_theme_path"):
                source = entry["dark_theme_path"]
                style = "dark"
            else:
                style = "color"
            return Path(entry["category"]) / style / Path(source).name
        return Path(entry["category"]) / Path(source).name

    @classmethod
    def _legacy_path(cls, icon_id: str, category: str | None) -> Path | None:
        candidates = []
        if category:
            candidates.extend((ICON_ROOT / category / f"{icon_id}.svg", ICON_ROOT / category / f"{icon_id}.png"))
        candidates.extend((ICON_ROOT / "ui" / f"{icon_id}.svg", ICON_ROOT / f"{icon_id}.svg", ICON_ROOT / f"{icon_id}.png"))
        return next((path for path in candidates if path.is_file()), None)

    @classmethod
    @lru_cache(maxsize=256)
    def icon(cls, icon_id: str, variant: str = "auto", category: str | None = None) -> QIcon:
        path = cls.path(icon_id, variant=variant, category=category)
        if path:
            if variant == "color":
                return QIcon(str(path))
            return QIcon(cls._monochrome_pixmap(path, QSize(64, 64)))
        fallbacks = {
            "back": QStyle.StandardPixmap.SP_ArrowBack,
            "forward": QStyle.StandardPixmap.SP_ArrowForward,
            "add": QStyle.StandardPixmap.SP_FileDialogNewFolder,
            "delete": QStyle.StandardPixmap.SP_TrashIcon,
            "refresh": QStyle.StandardPixmap.SP_BrowserReload,
            "save": QStyle.StandardPixmap.SP_DialogSaveButton,
        }
        app = QApplication.instance()
        return app.style().standardIcon(fallbacks[icon_id]) if app and icon_id in fallbacks else QIcon()

    @classmethod
    @lru_cache(maxsize=256)
    def pixmap(
        cls,
        icon_id: str,
        width: int,
        height: int | None = None,
        variant: str = "auto",
        category: str | None = None,
    ) -> QPixmap:
        target = QSize(width, height or width)
        path = cls.path(icon_id, variant=variant, category=category)
        if not path:
            return QPixmap()
        if variant == "color":
            source = QPixmap(str(path))
            return source.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return cls._monochrome_pixmap(path, target)

    @staticmethod
    def _monochrome_pixmap(path: Path, target: QSize) -> QPixmap:
        source = QPixmap(str(path)).scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if source.isNull():
            return source
        tinted = QPixmap(source.size())
        tinted.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor("#F2F3F7"))
        painter.end()
        return tinted

    @classmethod
    @lru_cache(maxsize=128)
    def tinted_pixmap(
        cls, icon_id: str, width: int, color: str, height: int | None = None, category: str | None = None,
    ) -> QPixmap:
        path = cls.path(icon_id, variant="dark", category=category)
        if not path:
            return QPixmap()
        source = QPixmap(str(path)).scaled(
            QSize(width, height or width), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
        if source.isNull():
            return source
        tinted = QPixmap(source.size())
        tinted.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()
        return tinted

    @classmethod
    def validate_approved(cls) -> list[str]:
        missing: list[str] = []
        for icon_id, entries in cls._load().items():
            for entry in entries:
                if entry.get("status") != "approved":
                    continue
                variant = "svg" if entry.get("format") == "svg" else "color"
                path = ICON_ROOT / cls._normalized_relative(entry, variant)
                if not path.is_file():
                    missing.append(f"{icon_id}:{variant}")
                if entry.get("dark_theme_path"):
                    dark_path = ICON_ROOT / cls._normalized_relative(entry, "dark")
                    if not dark_path.is_file():
                        missing.append(f"{icon_id}:dark")
        return missing
