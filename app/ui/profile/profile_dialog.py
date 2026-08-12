from PySide6.QtWidgets import QFileDialog, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout

from app.data.user_repository import LocalProfile, UserRepository
from app.ui.profile.profile_widgets import AvatarPicker, store_profile_avatar


class ProfileDialog(QDialog):
    def __init__(self, repository: UserRepository, games, parent=None) -> None:
        super().__init__(parent); self.repository = repository; self.games = list(games)
        self.setWindowTitle("МОЙ VELORA — локальный профиль"); self.setMinimumSize(680, 600)
        profile = repository.load_profile(); self._avatar_path = profile.avatar_path; root = QVBoxLayout(self)
        title = QLabel("МОЙ VELORA"); title.setStyleSheet("font-family:Georgia; font-size:24pt; letter-spacing:2px;"); root.addWidget(title)
        privacy = QLabel("Профиль и все личные данные хранятся только на этом компьютере. Они не отправляются на серверы Velora.")
        privacy.setObjectName("muted"); privacy.setWordWrap(True); root.addWidget(privacy)
        avatar_caption = QLabel("АВАТАР ПРОФИЛЯ")
        avatar_caption.setObjectName("caption")
        root.addWidget(avatar_caption)
        self.avatar_picker = AvatarPicker(profile.avatar_path)
        self.avatar_picker.custom_avatar_requested.connect(self._choose_avatar)
        self.avatar_picker.avatar_selected.connect(self._set_avatar_path)
        root.addWidget(self.avatar_picker)
        form = QFormLayout(); self.name = QLineEdit(profile.display_name); self.bio = QTextEdit(profile.bio); self.bio.setMaximumHeight(90)
        form.addRow("Имя", self.name); form.addRow("О себе", self.bio); root.addLayout(form)
        root.addStretch()
        buttons = QHBoxLayout(); buttons.addStretch(); close = QPushButton("Закрыть"); close.clicked.connect(self.reject)
        save = QPushButton("Сохранить профиль"); save.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF;"); save.clicked.connect(self._save)
        buttons.addWidget(close); buttons.addWidget(save); root.addLayout(buttons)

    def _save(self) -> None:
        name = self.name.text().strip() or "Пользователь"
        avatar_path = store_profile_avatar(self._avatar_path) if self._avatar_path else ""
        self.repository.save_profile(LocalProfile(name, self.bio.toPlainText().strip(), avatar_path)); self.accept()

    def _choose_avatar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите аватар", "", "Изображения (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._avatar_path = path
            self.avatar_picker.set_custom_avatar(path)

    def _set_avatar_path(self, path: str) -> None:
        self._avatar_path = path
