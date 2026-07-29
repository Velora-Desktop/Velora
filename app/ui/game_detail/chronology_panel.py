from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import resolve_resource_path


class ChronologyCard(QPushButton):
    def __init__(self, entry: dict[str, object], current_id: str, parent=None) -> None:
        super().__init__(parent)
        self.catalog_id = str(entry.get("catalog_id", "") or "")
        self.setEnabled(bool(self.catalog_id))
        self.setFixedSize(132, 238)
        self.setObjectName("chronologyCard")
        current_style = (
            "QPushButton#chronologyCard {border:2px solid #A33CFF;}"
            if self.catalog_id == current_id
            else ""
        )
        self.setStyleSheet(
            "QPushButton#chronologyCard {text-align:left;background:#0C151C;"
            "border:1px solid #2A3741;border-radius:5px;padding:6px;}"
            "QPushButton#chronologyCard:hover {background:#1D1030;border-color:#9B39FF;}"
            "QPushButton#chronologyCard:disabled {color:#D5DBE0;}"
            + current_style
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 6)
        layout.setSpacing(6)

        cover = QLabel("ОБЛОЖКА")
        cover.setFixedSize(110, 165)
        cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover.setStyleSheet("background:#17212A;color:#71808C;border:0;")
        path = str(entry.get("cover_path", "") or "")
        resolved = resolve_resource_path(path) if path else None
        if resolved and resolved.is_file():
            pixmap = QPixmap(str(resolved))
            cover.setPixmap(
                pixmap.scaled(
                    cover.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(cover, 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(str(entry.get("title", "Без названия")))
        title.setWordWrap(True)
        title.setMaximumHeight(38)
        title.setStyleSheet("font-weight:600;color:#F2F4F6;border:0;")
        layout.addWidget(title)
        year = entry.get("release_year") or "дата не объявлена"
        status = str(entry.get("status", "") or "")
        meta = QLabel(f"{year}" + (f" · {status}" if status else ""))
        meta.setWordWrap(True)
        meta.setStyleSheet("font-size:8pt;color:#91A0AB;border:0;")
        layout.addWidget(meta)
        layout.addStretch(1)


class ChronologyPanel(QFrame):
    catalog_item_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("chronologyPanel")
        self.setStyleSheet(
            "QFrame#chronologyPanel {background:#101820;"
            "border:1px solid #2A3640;border-radius:4px;}"
            "QFrame#chronologyPanel QScrollArea,"
            "QFrame#chronologyPanel QScrollArea > QWidget > QWidget {"
            "background:transparent;border:0;}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        self.title = QLabel("Хронология серии")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-size:18pt;font-weight:700;color:#F4F5F7;")
        root.addWidget(self.title)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFixedHeight(262)
        self.scroll.viewport().setStyleSheet("background:transparent;")
        root.addWidget(self.scroll)
        self.setVisible(False)

    def set_chronology(
        self,
        franchise_name: str,
        entries: list[dict[str, object]],
        current_id: str,
    ) -> None:
        container = QWidget()
        container.setObjectName("chronologyTrack")
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("background:transparent;border:0;")
        row = QHBoxLayout(container)
        row.setContentsMargins(2, 2, 2, 8)
        row.setSpacing(10)
        ordered = sorted(entries, key=lambda item: int(item.get("position", 0) or 0))
        for index, entry in enumerate(ordered):
            card = ChronologyCard(entry, current_id)
            if card.catalog_id:
                card.clicked.connect(
                    lambda checked=False, catalog_id=card.catalog_id:
                    self.catalog_item_requested.emit(catalog_id)
                )
            row.addWidget(card)
            if index < len(ordered) - 1:
                arrow = QLabel("›")
                arrow.setStyleSheet("font-size:27pt;color:#B653FF;")
                row.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        self.scroll.setWidget(container)
        self.title.setText(
            f"Хронология: {franchise_name}"
            if franchise_name
            else "Хронология серии"
        )
        self.setVisible(len(ordered) > 1)
