from PySide6.QtCore import QEvent, Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMenu, QPushButton, QWidgetAction,
)
from app.core.icon_registry import IconRegistry
from app.core.constants import APP_VERSION
from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.components import HoverAnimatedIcon


class VMenu(QMenu):
    settings_requested = Signal()
    about_requested = Signal()
    changelog_requested = Signal()
    support_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_labels: dict[QPushButton, QLabel] = {}
        self.addSection(f"VELORA {APP_VERSION}")
        self.settings_action = self._add_menu_row(
            "Настройки", self._request_settings,
            object_name="animatedSettingsMenuRow", animated_key="animated.settings",
        )
        self._add_menu_row(
            "О проекте", self.about_requested.emit,
            object_name="aboutMenuRow",
            animated_key="animated.info",
        )
        self._add_menu_row(
            "История изменений", self.changelog_requested.emit,
            object_name="changelogMenuRow",
            pixmap=IconRegistry.pixmap("history_recent", 20, variant="dark", category="ui"),
        )
        self._add_menu_row(
            "Поддержать Velora", self.support_requested.emit,
            object_name="supportMenuRow",
            pixmap=IconProvider.pixmap("service.boosty.light", 20),
        )
        self.addSeparator()
        self._add_menu_row(
            "Выход", self._quit, object_name="exitMenuRow",
            animated_key="animated.exit",
        )

    def _add_menu_row(
        self,
        text: str,
        callback,
        *,
        object_name: str,
        pixmap=None,
        animated_key: str | None = None,
        autoplay: bool = False,
    ) -> QWidgetAction:
        """Add a menu row with one fixed icon column shared by every action."""
        action = QWidgetAction(self)
        row = QPushButton()
        row.setObjectName(object_name)
        row.setProperty("hovered", False)
        row.setFixedHeight(58)
        row.setMinimumWidth(190)
        row.setStyleSheet(
            "QPushButton{background:transparent;border:0;border-radius:4px;"
            "text-align:left;padding:0;}"
            "QPushButton:hover,QPushButton[hovered=\"true\"]{"
            "background:#1A0D2B;border:0;}"
            "QLabel{background:transparent;}"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(10)
        if animated_key:
            icon = HoverAnimatedIcon(
                animated_key, 20, row, mouse_transparent=True,
                autoplay=autoplay, frame_interval_ms=41,
            )
            icon.setObjectName(
                "menuAnimatedSettingsIcon"
                if animated_key == "animated.settings"
                else f"{object_name}AnimatedIcon"
            )
            icon.attach_hover_source(row)
        else:
            icon = QLabel(row)
            icon.setPixmap(pixmap)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(20, 20)
            icon.setObjectName(f"{object_name}Icon")
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
        label = QLabel(text, row)
        label.setObjectName(f"{object_name}Label")
        label.setStyleSheet("color:#FFFFFF;background:transparent;")
        layout.addWidget(label)
        layout.addStretch(1)
        self._hover_labels[row] = label
        row.installEventFilter(self)
        action.setDefaultWidget(row)
        self.addAction(action)
        row.clicked.connect(
            lambda checked=False, target=callback: self._trigger_menu_callback(target)
        )
        return action

    def eventFilter(self, watched, event) -> bool:
        label = self._hover_labels.get(watched)
        if label is not None:
            if event.type() == QEvent.Type.Enter:
                watched.setProperty("hovered", True)
                watched.style().unpolish(watched)
                watched.style().polish(watched)
                label.setStyleSheet("color:#C77DFF;background:transparent;")
            elif event.type() == QEvent.Type.Leave:
                watched.setProperty("hovered", False)
                watched.style().unpolish(watched)
                watched.style().polish(watched)
                label.setStyleSheet("color:#FFFFFF;background:transparent;")
        return super().eventFilter(watched, event)

    def _trigger_menu_callback(self, callback) -> None:
        self.close()
        callback()

    def _request_settings(self) -> None:
        self.close()
        self.settings_requested.emit()

    @staticmethod
    def _quit() -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
