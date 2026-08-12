from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import ACCENT
from app.ui.velora_ui.components import AnimatedSearchLineEdit


def _normalize_tag(value: str) -> str:
    return " ".join(value.strip().lstrip("#").strip().casefold().split())


class SearchPage(QWidget):
    item_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.items = []
        self._tag_query = ""
        root = QVBoxLayout(self); root.setContentsMargins(34, 24, 34, 28); root.setSpacing(14)
        title = QLabel("ГЛОБАЛЬНЫЙ ПОИСК"); title.setStyleSheet("font-family:Georgia;font-size:25pt;"); root.addWidget(title)
        subtitle = QLabel("Ищите игры, фильмы, сериалы и программы во всём официальном каталоге Velora."); subtitle.setObjectName("muted"); root.addWidget(subtitle)
        self.search = AnimatedSearchLineEdit(icon_size=22); self.search.setPlaceholderText("Введите название, категорию, автора или платформу…"); self.search.setMinimumHeight(52)
        self.search.setStyleSheet(f"QLineEdit{{font-size:13pt;padding:10px 16px;border:1px solid {ACCENT};border-radius:8px;background:#081119;}}")
        self.search.textChanged.connect(self._rebuild); root.addWidget(self.search)
        self.count = QLabel(); self.count.setObjectName("muted"); root.addWidget(self.count)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget(); self.results = QVBoxLayout(self.content); self.results.setContentsMargins(0,0,0,0); self.results.setSpacing(7); self.scroll.setWidget(self.content); root.addWidget(self.scroll,1)

    def set_items(self, items) -> None:
        self.items = list(items); self._rebuild()

    def focus_search(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason); self.search.selectAll()

    def set_tag_query(self, tag: str) -> None:
        """Open a strict tag search without matching arbitrary metadata."""
        normalized = _normalize_tag(tag)
        self._tag_query = normalized
        unchanged = self.search.text() == normalized
        self.search.setText(normalized)
        if unchanged:
            self._rebuild()
        self.focus_search()

    def _rebuild(self, *_args) -> None:
        while self.results.count():
            item = self.results.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        query = self.search.text().strip().casefold()
        normalized_query = _normalize_tag(query)
        if not query:
            self._tag_query = ""
            matches = []
        elif self._tag_query and normalized_query == self._tag_query:
            matches = [
                item for item in self.items
                if self._tag_query in {
                    _normalize_tag(tag)
                    for tag in (*item.system_tags, *item.tags)
                }
            ]
        else:
            self._tag_query = ""
            matches = [
                item for item in self.items
                if query in " ".join((
                    item.title, item.media_type, item.category, item.subgroup,
                    item.developer, item.platform,
                )).casefold()
            ]
        self.count.setText("Начните ввод для поиска по 40 карточкам" if not query else f"Найдено: {len(matches)}")
        for item in matches:
            row = QFrame(); row.setStyleSheet("QFrame{background:#09131A;border:1px solid #22323D;border-radius:7px;}QFrame:hover{border-color:#8B2CF5;background:#101526;}")
            layout = QHBoxLayout(row); layout.setContentsMargins(14,10,14,10)
            text = QVBoxLayout(); name = QPushButton(item.title); name.setStyleSheet(f"text-align:left;border:0;font-size:12pt;font-weight:650;background:transparent;QPushButton:hover{{color:{ACCENT};}}")
            name.clicked.connect(lambda checked=False, catalog_id=item.catalog_id:self.item_requested.emit(catalog_id)); text.addWidget(name)
            meta = QLabel(f"{item.media_type}  ·  {item.category}  ·  {item.subgroup}"); meta.setObjectName("muted"); text.addWidget(meta); layout.addLayout(text,1)
            score = QLabel(item.general_score); score.setStyleSheet("font-size:16pt;font-weight:700;color:#18D647;"); layout.addWidget(score)
            self.results.addWidget(row)
        self.results.addStretch()
