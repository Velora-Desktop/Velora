from __future__ import annotations

from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QSize, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app.core.icon_registry import IconRegistry
from app.core.paths import APP_DATA_DIR, LOGS_DIR
from app.services.data_backup_service import BackupValidationError, DataBackupService


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
    backup_imported = Signal()

    def __init__(self, hide_adult_content: bool, games=(), parent=None, data_service: DataBackupService | None = None) -> None:
        super().__init__(parent)
        self.games = list(games)
        self.data_service = data_service
        self.setWindowTitle("Настройки Velora")
        self.setWindowIcon(IconRegistry.icon("settings_gears", variant="dark", category="ui"))
        self.setMinimumSize(680, 520)
        root = QVBoxLayout(self)
        title = QLabel("НАСТРОЙКИ"); title.setStyleSheet("font-size:18pt;font-weight:600;")
        root.addWidget(title)
        tabs = QTabWidget(); root.addWidget(tabs, 1)
        tabs.addTab(self._build_general_tab(), "ОБЩЕЕ")
        tabs.addTab(self._build_content_tab(hide_adult_content), "КОНТЕНТ")
        tabs.addTab(self._build_data_tab(), "ДАННЫЕ")
        tabs.addTab(self._build_diagnostics_tab(), "ДИАГНОСТИКА")
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

    def _build_data_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(12)
        layout.addWidget(QLabel("РЕЗЕРВНЫЕ КОПИИ"))
        hint = QLabel("Резервная копия содержит локальный профиль, оценки, статусы, историю, настройки и пользовательские изображения.")
        hint.setObjectName("muted"); hint.setWordWrap(True); layout.addWidget(hint)
        actions = QHBoxLayout()
        export_button = QPushButton("ЭКСПОРТИРОВАТЬ КОПИЮ")
        export_button.setIcon(IconRegistry.icon("export_backup", category="diagnostics"))
        export_button.clicked.connect(self._export_backup)
        import_button = QPushButton("ИМПОРТИРОВАТЬ КОПИЮ")
        import_button.setIcon(IconRegistry.icon("import_backup", category="diagnostics"))
        import_button.clicked.connect(self._import_backup)
        actions.addWidget(export_button); actions.addWidget(import_button); layout.addLayout(actions)
        layout.addWidget(QLabel("ИСПОЛЬЗОВАНИЕ ХРАНИЛИЩА"))
        self.storage_values = QFormLayout(); layout.addLayout(self.storage_values)
        self._refresh_storage_sizes()
        layout.addStretch()
        return tab

    def _build_diagnostics_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(10)
        layout.addWidget(QLabel("ДИАГНОСТИКА БАЗ ДАННЫХ"))
        for text, icon, callback in (
            ("ПРОВЕРИТЬ USER.DB", "database_check", lambda: self._check_database("user")),
            ("ПРОВЕРИТЬ CATALOG.DB", "integrity_check", lambda: self._check_database("catalog")),
            ("ОТКРЫТЬ ПАПКУ ДАННЫХ", "data_folder", lambda: self._open_folder(APP_DATA_DIR)),
            ("ОТКРЫТЬ ПАПКУ ЛОГОВ", "logs", lambda: self._open_folder(LOGS_DIR)),
        ):
            button = QPushButton(text); button.setIcon(IconRegistry.icon(icon)); button.clicked.connect(callback); layout.addWidget(button)
        self.version_info = QLabel(self._version_text()); self.version_info.setObjectName("muted"); layout.addWidget(self.version_info)
        layout.addStretch()
        return tab

    def _refresh_storage_sizes(self) -> None:
        while self.storage_values.rowCount(): self.storage_values.removeRow(0)
        if self.data_service is None:
            self.storage_values.addRow(QLabel("Данные недоступны")); return
        sizes = self.data_service.storage_sizes()
        labels = (("Официальный каталог", "catalog"), ("Обложки", "covers"), ("Пользовательская база", "user_db"), ("Пользовательские изображения", "user_images"), ("Резервные копии", "backups"), ("Всего", "total"))
        for title, key in labels: self.storage_values.addRow(title, QLabel(self._format_bytes(sizes[key])))

    def _export_backup(self) -> None:
        if self.data_service is None: return
        suggested = str(Path.home() / "Documents" / f"Velora_Backup_{datetime.now():%Y-%m-%d_%H-%M}.zip")
        target, _ = QFileDialog.getSaveFileName(self, "Экспорт резервной копии", suggested, "Velora Backup (*.zip)")
        if not target: return
        try:
            path = self.data_service.export_backup(Path(target))
            self._refresh_storage_sizes(); QMessageBox.information(self, "Velora", f"Резервная копия создана:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))

    def _import_backup(self) -> None:
        if self.data_service is None: return
        source, _ = QFileDialog.getOpenFileName(self, "Импорт резервной копии", str(Path.home()), "Velora Backup (*.zip)")
        if not source: return
        answer = QMessageBox.warning(self, "Замена локальных данных", "Текущие локальные данные будут заменены после проверки архива. Перед заменой Velora создаст автоматическую копию. Продолжить?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes: return
        try:
            self.data_service.import_backup(Path(source))
            QMessageBox.information(self, "Velora", "Данные восстановлены. Velora будет перезапущена при следующем запуске.")
            self.backup_imported.emit(); self.accept()
        except (BackupValidationError, OSError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка импорта", str(exc))

    def _check_database(self, kind: str) -> None:
        if self.data_service is None: return
        database = self.data_service.user_db if kind == "user" else self.data_service.catalog_db
        ok, message = self.data_service.integrity_check(database)
        if ok: QMessageBox.information(self, "Проверка базы", message)
        else: QMessageBox.warning(self, "Проверка базы", message + "\n\nФайл не изменён. Используйте проверенную резервную копию для восстановления.")

    def _version_text(self) -> str:
        if self.data_service is None: return "Версии баз недоступны"
        values = self.data_service.versions()
        return f"Velora: {values['application']}\nСхема user.db: {values['user_schema']}\nСхема catalog.db: {values['catalog_schema']}"

    @staticmethod
    def _open_folder(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @staticmethod
    def _format_bytes(value: int) -> str:
        amount = float(value)
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if amount < 1024 or unit == "ГБ": return f"{amount:.1f} {unit}"
            amount /= 1024
        return f"{amount:.1f} ГБ"

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
