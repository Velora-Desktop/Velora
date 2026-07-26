from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from app.ui.navigation.v_menu import VMenu
from app.core.icon_registry import IconRegistry


class TopBar(QFrame):
    placeholder_requested = Signal()
    back_requested = Signal()
    forward_requested = Signal()
    profile_requested = Signal()
    section_requested = Signal(str)
    search_requested = Signal()
    custom_catalog_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(70)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        logo = QPushButton("V")
        logo.setObjectName("veloraLogo")
        logo.setFixedSize(58, 52)
        logo.setStyleSheet("font-family: Georgia; font-size: 30pt; font-weight: 700; padding:0;")
        logo_glow = QGraphicsDropShadowEffect(logo)
        logo_glow.setBlurRadius(16)
        logo_glow.setOffset(0, 0)
        logo_glow.setColor(QColor(175, 104, 255, 145))
        logo.setGraphicsEffect(logo_glow)
        self.menu = VMenu(self)
        logo.clicked.connect(lambda: self.menu.popup(logo.mapToGlobal(logo.rect().bottomLeft())))
        layout.addWidget(logo)

        history_buttons = []
        for icon_id, tooltip in (("back", "Назад"), ("forward", "Вперёд")):
            button = QPushButton()
            button.setIcon(IconRegistry.icon(icon_id))
            button.setIconSize(QSize(18, 18))
            button.setFixedSize(40, 40)
            button.setToolTip(tooltip)
            button.setEnabled(False)
            button.setStyleSheet(
                "font-family:'Segoe UI Symbol'; font-size:16pt; padding:0;"
            )
            layout.addWidget(button)
            history_buttons.append(button)
        self.back_button, self.forward_button = history_buttons
        self.back_button.clicked.connect(self.back_requested)
        self.forward_button.clicked.connect(self.forward_requested)

        self.section_back = QPushButton("‹")
        self.section_back.setObjectName("sectionScrollButton")
        self.section_back.setFixedSize(30, 40)
        self.section_back.setToolTip("Предыдущие разделы")
        self.section_back.clicked.connect(lambda: self._shift_sections(-1))
        self.section_back.hide()
        layout.addWidget(self.section_back)

        self.section_scroll = QScrollArea()
        self.section_scroll.setObjectName("sectionScroll")
        self.section_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.section_scroll.setStyleSheet(
            "QScrollArea#sectionScroll, QWidget#sectionStrip {"
            "background:transparent; border:0;}"
        )
        self.section_scroll.setWidgetResizable(False)
        self.section_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.section_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.section_scroll.setFixedHeight(54)
        self.section_scroll.setMinimumWidth(420)
        self.section_scroll.setMaximumWidth(1050)
        self.section_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.section_container = QWidget()
        self.section_container.setObjectName("sectionStrip")
        self.section_layout = QHBoxLayout(self.section_container)
        self.section_layout.setContentsMargins(0, 0, 0, 0)
        self.section_layout.setSpacing(4)
        self.section_scroll.setWidget(self.section_container)
        layout.addWidget(self.section_scroll, 1)

        self.section_buttons = []
        self._space_glows = {}
        for index, text in enumerate(("ИГРЫ", "ФИЛЬМЫ", "СЕРИАЛЫ", "ПРОГРАММЫ")):
            button = self._make_section_button(text, text)
            button.setProperty("active", index == 0)
            self._space_glows[button].setEnabled(index == 0)
            self.section_layout.addWidget(button)
            self.section_buttons.append(button)

        self._custom_sections = []
        self.custom_buttons = []
        self.section_forward = QPushButton("›")
        self.section_forward.setObjectName("sectionScrollButton")
        self.section_forward.setFixedSize(30, 40)
        self.section_forward.setToolTip("Следующие разделы")
        self.section_forward.clicked.connect(lambda: self._shift_sections(1))
        self.section_forward.hide()
        layout.addWidget(self.section_forward)
        self._section_animation = QPropertyAnimation(
            self.section_scroll.horizontalScrollBar(), b"value", self
        )
        self._section_animation.setDuration(230)
        self._section_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.section_scroll.horizontalScrollBar().valueChanged.connect(
            self._update_section_arrows
        )

        for action in ("search", "add"):
            button = QPushButton()
            button.setIcon(IconRegistry.icon(action))
            button.setIconSize(QSize(19, 19))
            button.setToolTip("Глобальный поиск" if action == "search" else "Создать раздел")
            if action == "search":
                self.search_button = button
                button.clicked.connect(self.search_requested)
            else:
                self.add_button = button
                button.clicked.connect(self.custom_catalog_requested)
            button.setFixedSize(44, 40)
            button.setStyleSheet("border:1px solid #27313A; border-radius:7px; background:#070B10;" if action == "add" else "")
            layout.addWidget(button)

        # Search and add remain attached to the section strip, while the
        # profile entry is anchored to the far-right edge of the window.
        layout.addStretch(1)

        self.profile_button = QPushButton("МОЙ VELORA")
        self.profile_button.setMinimumWidth(210)
        self.profile_button.setStyleSheet("font-family: Georgia; font-size:18pt; letter-spacing:1.5px; padding:8px 14px;")
        profile_glow = QGraphicsDropShadowEffect(self.profile_button)
        profile_glow.setBlurRadius(12)
        profile_glow.setOffset(0, 0)
        profile_glow.setColor(QColor(143, 54, 255, 120))
        profile_glow.setEnabled(False)
        self.profile_button.setGraphicsEffect(profile_glow)
        self._space_glows[self.profile_button] = profile_glow
        self.profile_button.clicked.connect(self.profile_requested)
        layout.addWidget(self.profile_button)
        QTimer.singleShot(0, self._sync_section_strip)

    def set_custom_sections(self, names: list[str]) -> None:
        self._section_animation.stop()
        active = next(
            (
                button.property("sectionName")
                for button in self.custom_buttons
                if button.property("active")
            ),
            None,
        )
        for button in self.custom_buttons:
            self.section_layout.removeWidget(button)
            self._space_glows.pop(button, None)
            button.hide()
            button.deleteLater()
        self.custom_buttons.clear()
        self._custom_sections = list(names)
        for name in self._custom_sections:
            button = self._make_section_button(name.upper(), name)
            button.setProperty("active", name == active)
            self.section_layout.addWidget(button)
            self.custom_buttons.append(button)
        self._sync_section_strip()

    def prepare_section_removal(self) -> None:
        """Stop strip motion before its button set is destructively rebuilt."""
        self._section_animation.stop()
        self.section_scroll.horizontalScrollBar().setValue(0)

    def _make_section_button(self, text: str, section_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setFixedHeight(50)
        button.setMinimumWidth(98)
        button.setMaximumWidth(190)
        button.setToolTip(section_name)
        button.setProperty("sectionName", section_name)
        button.setStyleSheet(
            "font-family:'Segoe UI'; font-size:12pt; letter-spacing:0.4px;"
            "padding:8px 12px;"
        )
        glow = QGraphicsDropShadowEffect(button)
        glow.setBlurRadius(18)
        glow.setOffset(0, 3)
        glow.setColor(QColor(143, 54, 255, 120))
        glow.setEnabled(False)
        button.setGraphicsEffect(glow)
        self._space_glows[button] = glow
        button.clicked.connect(
            lambda checked=False, name=section_name: self.section_requested.emit(name)
        )
        return button

    def _sync_section_strip(self) -> None:
        self.section_layout.invalidate()
        self.section_layout.activate()
        buttons = self.section_buttons + self.custom_buttons
        widths = [
            max(
                button.minimumWidth(),
                min(button.sizeHint().width(), button.maximumWidth()),
            )
            for button in buttons
        ]
        total_width = (
            sum(widths)
            + max(0, len(widths) - 1) * self.section_layout.spacing()
        )
        available_width = max(420, min(1050, self.width() - 600))
        self.section_scroll.setFixedWidth(min(total_width, available_width))
        self.section_container.setFixedSize(max(1, total_width), 54)
        QTimer.singleShot(0, self._restore_active_section_position)

    def _restore_active_section_position(self) -> None:
        active = next(
            (
                button
                for button in self.section_buttons + self.custom_buttons
                if button.property("active")
            ),
            None,
        )
        if active is not None:
            self.section_scroll.ensureWidgetVisible(active, 18, 0)
        self._update_section_arrows()

    def _shift_sections(self, direction: int) -> None:
        bar = self.section_scroll.horizontalScrollBar()
        target = max(0, min(bar.maximum(), bar.value() + direction * 150))
        self._section_animation.stop()
        self._section_animation.setStartValue(bar.value())
        self._section_animation.setEndValue(target)
        self._section_animation.start()

    def _update_section_arrows(self, *_args) -> None:
        bar = self.section_scroll.horizontalScrollBar()
        has_overflow = bar.maximum() > 0
        self.section_back.setVisible(has_overflow and bar.value() > 0)
        self.section_forward.setVisible(has_overflow and bar.value() < bar.maximum())
        self.section_back.setEnabled(bar.value() > 0)
        self.section_forward.setEnabled(bar.value() < bar.maximum())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._sync_section_strip)

    def set_profile_active(self, active: bool) -> None:
        self.profile_button.setProperty("active", active)
        if active:
            for button in self.section_buttons:
                button.setProperty("active", False)
                button.style().unpolish(button); button.style().polish(button)
            for button in self.custom_buttons:
                button.setProperty("active",False); button.style().unpolish(button); button.style().polish(button)
        self.profile_button.style().unpolish(self.profile_button); self.profile_button.style().polish(self.profile_button)
        self._refresh_space_glows()

    def set_search_active(self, active: bool) -> None:
        self.search_button.setProperty("active", active)
        self.search_button.setStyleSheet(
            "border-bottom:2px solid #8B2CF5; background:#120B1D;" if active else ""
        )

    def set_active_space(self, name: str) -> None:
        self.profile_button.setProperty("active", name == "МОЙ VELORA")
        active_button = None
        for button in self.section_buttons:
            button.setProperty("active", button.property("sectionName") == name)
            if button.property("active"):
                active_button = button
            button.style().unpolish(button); button.style().polish(button)
        for button in self.custom_buttons:
            button.setProperty("active",button.property("sectionName")==name)
            if button.property("active"):
                active_button = button
            button.style().unpolish(button); button.style().polish(button)
        self.profile_button.style().unpolish(self.profile_button); self.profile_button.style().polish(self.profile_button)
        self._refresh_space_glows()
        if active_button is not None:
            self.section_scroll.ensureWidgetVisible(active_button, 18, 0)
            QTimer.singleShot(0, self._update_section_arrows)

    def _refresh_space_glows(self) -> None:
        for button, effect in self._space_glows.items():
            effect.setEnabled(bool(button.property("active")))
