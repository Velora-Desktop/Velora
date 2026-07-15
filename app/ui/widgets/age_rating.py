from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.core.icon_registry import IconRegistry


class AgeRatingValue(QWidget):
    """Compact age value; the red restriction icon exists only for 18+."""

    def __init__(self, rating: int | str = 0, *, centered: bool = False, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.value = QLabel()
        self.value.setStyleSheet("font-weight:500;color:#E7E9EC;background:transparent;border:0;")
        self.icon = QLabel()
        self.icon.setFixedSize(19, 19)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setToolTip("Контент предназначен только для совершеннолетних")
        if centered:
            # Reserve an equal slot on the left so the value remains exactly
            # on the column axis while the restriction icon sits to its right.
            left_balance = QWidget()
            left_balance.setObjectName("ageBalance")
            left_balance.setStyleSheet("QWidget#ageBalance { background:transparent; border:0; }")
            left_balance.setFixedWidth(self.icon.width())
            layout.addWidget(left_balance)
            self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.value, 1)
            layout.addWidget(self.icon)
        else:
            layout.addWidget(self.value)
            layout.addWidget(self.icon)
            layout.addStretch(1)
        self.setText(rating)

    def setText(self, rating: int | str) -> None:
        text = str(rating).strip().removesuffix("+") or "0"
        self.value.setText(f"{text}+")
        adult = text == "18"
        # Keep the transparent slot in the layout for non-18 ratings; hiding
        # the widget would collapse the slot and shift the text off-center.
        self.icon.setVisible(True)
        self.icon.setToolTip("Контент предназначен только для совершеннолетних" if adult else "")
        self.icon.setPixmap(
            IconRegistry.tinted_pixmap("age_18", 17, "#FF4D57", category="age")
            if adult else QPixmap()
        )
        self.setStyleSheet("AgeRatingValue { background:transparent; border:0; }")
