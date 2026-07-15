from __future__ import annotations

from PySide6.QtCore import QSize, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app.core.icon_registry import IconRegistry


LANGUAGES = (
    ("Русский", "language_ru", True),
    ("English (US)", "language_en_us", False),
    ("English (UK)", "language_en_gb", False),
    ("Deutsch", "language_de", False),
    ("Español", "language_es", False),
    ("Français", "language_fr", False),
    ("Română", "language_ro", False),
)


class SettingsDialog(QDialog):
    adult_filter_changed = Signal(bool)
    hidden_restored = Signal(object)
    profile_reset_requested = Signal()

    def __init__(self, hide_adult_content: bool, games=(), parent=None) -> None:
        super().__init__(parent)
        self.games = list(games)
        self.setWindowTitle("Настройки Velora")
        self.setWindowIcon(IconRegistry.icon("settings_gears", variant="dark", category="ui"))
        self.setMinimumSize(680, 520)
        root = QVBoxLayout(self)
        title = QLabel("НАСТРОЙКИ"); title.setStyleSheet("font-size:18pt;font-weight:600;")
        root.addWidget(title)
        tabs = QTabWidget(); root.addWidget(tabs, 1)
        tabs.addTab(self._build_general_tab(), "ОБЩЕЕ")
        tabs.addTab(self._build_content_tab(hide_adult_content), "КОНТЕНТ")
        tabs.addTab(self._build_language_tab(), "ЯЗЫК")

    def _build_general_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("ОБЩЕЕ"))
        layout.addWidget(QLabel("Локальные настройки интерфейса Velora."))
        layout.addStretch()
        title = QLabel("СБРОС ЛОКАЛЬНЫХ ДАННЫХ"); title.setStyleSheet("color:#FF6868;font-weight:600;")
        layout.addWidget(title)
        text = QLabel("Удаляет профиль, личные оценки, статусы, время, избранное, скрытые карточки и историю. Официальный каталог не изменяется.")
        text.setObjectName("muted"); text.setWordWrap(True); layout.addWidget(text)
        reset = QPushButton("СБРОСИТЬ ЛОКАЛЬНЫЙ ПРОФИЛЬ")
        reset.setProperty("danger", True)
        reset.clicked.connect(self._confirm_reset); layout.addWidget(reset)
        return tab

    def _build_content_tab(self, hide_adult_content: bool) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.adult_filter = QCheckBox("Скрывать карточки 18+")
        self.adult_filter.setChecked(hide_adult_content)
        self.adult_filter.toggled.connect(self.adult_filter_changed)
        layout.addWidget(self.adult_filter)
        layout.addWidget(QLabel("СКРЫТЫЕ ОБЪЕКТЫ · ИГРЫ / ФИЛЬМЫ / СЕРИАЛЫ / ПРОГРАММЫ"))
        self.hidden = QListWidget(); self._refresh(); layout.addWidget(self.hidden, 1)
        row = QHBoxLayout(); row.addStretch()
        restore = QPushButton("ВЕРНУТЬ В КАТАЛОГ"); restore.clicked.connect(self._restore); row.addWidget(restore)
        layout.addLayout(row)
        return tab

    def _build_language_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab)
        heading = QHBoxLayout()
        globe = QLabel(); globe.setPixmap(IconRegistry.pixmap("globe", 22, variant="dark", category="ui"))
        heading.addWidget(globe); heading.addWidget(QLabel("ЯЗЫК ИНТЕРФЕЙСА")); heading.addStretch(); layout.addLayout(heading)
        hint = QLabel("Перевод интерфейса будет добавляться постепенно. Сейчас доступен русский язык.")
        hint.setObjectName("muted"); hint.setWordWrap(True); layout.addWidget(hint)
        for name, icon_id, available in LANGUAGES:
            button = QPushButton(name if available else f"{name}     ПОЗЖЕ")
            button.setIcon(IconRegistry.icon(icon_id, variant="color", category="languages"))
            button.setIconSize(QSize(24, 18)); button.setMinimumHeight(42)
            button.setProperty("active", available)
            button.setProperty("future", not available)
            button.setStyleSheet("text-align:left;padding:8px 12px;")
            if not available:
                button.setToolTip("Перевод появится в одной из следующих версий Velora")
            if not available:
                button.clicked.connect(self._language_placeholder)
            layout.addWidget(button)
        layout.addStretch()
        return tab

    def _language_placeholder(self) -> None:
        QMessageBox.information(self, "Язык интерфейса", "Перевод интерфейса появится в одной из следующих версий Velora.")

    def _refresh(self) -> None:
        self.hidden.clear()
        for game in self.games:
            if game.hidden:
                self.hidden.addItem(f"{game.media_type}  /  {game.title}")
                self.hidden.item(self.hidden.count() - 1).setData(Qt.ItemDataRole.UserRole, game)

    def _restore(self) -> None:
        item = self.hidden.currentItem()
        if item is None:
            return
        game = item.data(Qt.ItemDataRole.UserRole); game.hidden = False
        self.hidden_restored.emit(game); self._refresh()

    def _confirm_reset(self) -> None:
        answer = QMessageBox.warning(
            self,
            "Сброс локального профиля",
            "Все личные данные Velora будут удалены без возможности восстановления.\n\nПродолжить?",
            QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Reset:
            self.profile_reset_requested.emit(); self.accept()
