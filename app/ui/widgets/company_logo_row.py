from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.core.company_logos import resolve_company_logo, split_company_names
from app.core.icon_registry import IconRegistry


class CompanyLogoRow(QWidget):
    """Compact company metadata; missing logos degrade to ordinary text."""

    def __init__(self, parent=None, max_visible: int = 2, compact: bool = False) -> None:
        super().__init__(parent)
        self._max_visible = max_visible
        self._compact = compact
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def setText(self, value: str) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        names = split_company_names(value)
        # Company metadata is logo-first on every surface. Prefer the first
        # reviewed company even when an unresolvable person/entity precedes it.
        matched = next((name for name in names if resolve_company_logo(name)), None)
        visible_names = [matched] if matched else names[:1]
        for index, name in enumerate(visible_names):
            semantic_id = resolve_company_logo(name)
            if semantic_id:
                group_names = [candidate for candidate in names
                               if resolve_company_logo(candidate) == semantic_id]
                icon = QLabel()
                icon.setFixedSize(QSize(44 if self._compact else 76, 26 if self._compact else 32))
                icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon.setPixmap(IconRegistry.pixmap(
                    semantic_id, 42 if self._compact else 72,
                    24 if self._compact else 30,
                    variant="original", category="company"
                ))
                # A single parent-brand logo represents all aliases/subsidiaries
                # from the source value; the hover text preserves their names.
                icon.setToolTip("\n".join(group_names))
                icon.setStyleSheet("QLabel:hover { background:#160B24; border-radius:3px; }")
                self._layout.addWidget(icon)
            if not semantic_id:
                text = QLabel(name)
                text.setStyleSheet(
                    "font-size:9.5pt; font-weight:500;" if self._compact
                    else "font-size:11pt; font-weight:500;"
                )
                self._layout.addWidget(text)
            if index + 1 < len(visible_names):
                separator = QLabel("·")
                separator.setObjectName("muted")
                self._layout.addWidget(separator)
        visible_ids = {resolve_company_logo(name) for name in visible_names
                       if resolve_company_logo(name)}
        hidden_names = [name for name in names
                        if name not in visible_names
                        and resolve_company_logo(name) not in visible_ids]
        if hidden_names:
            more = QLabel(f"+{len(hidden_names)}")
            more.setToolTip("; ".join(hidden_names))
            more.setObjectName("muted")
            self._layout.addWidget(more)
        if not names:
            self._layout.addWidget(QLabel("—"))
        self._layout.addStretch(1)
        self.setToolTip("; ".join(names))

    def setToolTip(self, text: str) -> None:
        super().setToolTip(text)
