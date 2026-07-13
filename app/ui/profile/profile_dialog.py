from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout

from app.data.user_repository import LocalProfile, UserRepository


class ProfileDialog(QDialog):
    def __init__(self, repository: UserRepository, games, parent=None) -> None:
        super().__init__(parent); self.repository = repository; self.games = list(games)
        self.setWindowTitle("МОЙ VELORA — локальный профиль"); self.setMinimumSize(680, 520)
        profile = repository.load_profile(); root = QVBoxLayout(self)
        title = QLabel("МОЙ VELORA"); title.setStyleSheet("font-family:Georgia; font-size:24pt; letter-spacing:2px;"); root.addWidget(title)
        privacy = QLabel("Профиль и все личные данные хранятся только на этом компьютере. Они не отправляются на серверы Velora.")
        privacy.setObjectName("muted"); privacy.setWordWrap(True); root.addWidget(privacy)
        form = QFormLayout(); self.name = QLineEdit(profile.display_name); self.bio = QTextEdit(profile.bio); self.bio.setMaximumHeight(90)
        form.addRow("Имя", self.name); form.addRow("О себе", self.bio); root.addLayout(form)
        stats = QLabel(self._statistics()); stats.setStyleSheet("background:#09131A; border:1px solid #273640; border-radius:8px; padding:18px; font-size:11pt;")
        root.addWidget(stats); root.addStretch()
        buttons = QHBoxLayout(); buttons.addStretch(); close = QPushButton("Закрыть"); close.clicked.connect(self.reject)
        save = QPushButton("Сохранить профиль"); save.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF;"); save.clicked.connect(self._save)
        buttons.addWidget(close); buttons.addWidget(save); root.addLayout(buttons)

    def _statistics(self) -> str:
        rated = sum(game.personal_score != "—" for game in self.games)
        favorites = sum(game.favorite for game in self.games)
        started = sum(game.status and game.status != "НЕ НАЧИНАЛ" for game in self.games)
        return f"ЛИЧНАЯ СТАТИСТИКА\n\nОценено игр: {rated}\nНачато или завершено: {started}\nВ избранном: {favorites}\nВсего объектов в каталоге: {len(self.games)}"

    def _save(self) -> None:
        name = self.name.text().strip() or "Пользователь"
        self.repository.save_profile(LocalProfile(name, self.bio.toPlainText().strip(), "")); self.accept()
