from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QLabel, QLineEdit, QPushButton,
    QRadioButton, QVBoxLayout,
)


class FirstRunDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Первый запуск Velora")
        self.setModal(True); self.setMinimumWidth(580)
        root = QVBoxLayout(self); root.setSpacing(12)
        title = QLabel("ДОБРО ПОЖАЛОВАТЬ В VELORA"); title.setStyleSheet("font-size:18pt;font-weight:600;"); root.addWidget(title)
        intro = QLabel("Все данные профиля и личной библиотеки хранятся только на этом компьютере.")
        intro.setObjectName("muted"); intro.setWordWrap(True); root.addWidget(intro)
        self.create_profile = QCheckBox("Создать локальный профиль")
        self.create_profile.setChecked(True); root.addWidget(self.create_profile)
        self.profile_name = QLineEdit(); self.profile_name.setPlaceholderText("Введите имя"); root.addWidget(self.profile_name)
        self.create_profile.toggled.connect(self.profile_name.setEnabled)
        content_title = QLabel("КОНТЕНТ 18+"); content_title.setStyleSheet("font-size:12pt;font-weight:600;margin-top:10px;"); root.addWidget(content_title)
        self.hide_adult = QRadioButton("Скрывать контент 18+ (рекомендуется)")
        self.show_adult = QRadioButton("Показывать контент 18+")
        group = QButtonGroup(self); group.addButton(self.hide_adult); group.addButton(self.show_adult)
        self.hide_adult.setChecked(True); root.addWidget(self.hide_adult); root.addWidget(self.show_adult)
        hint = QLabel("Вы сможете изменить этот выбор позже: Настройки → Контент.")
        hint.setObjectName("muted"); root.addWidget(hint)
        proceed = QPushButton("ПРОДОЛЖИТЬ"); proceed.setMinimumHeight(40); proceed.setStyleSheet("background:#6E1BC4;border:1px solid #A54BFF;font-weight:600;")
        proceed.clicked.connect(self.accept); root.addWidget(proceed)

    @property
    def profile_requested(self) -> bool:
        return self.create_profile.isChecked()

    @property
    def display_name(self) -> str:
        return self.profile_name.text().strip() or "Пользователь"

    @property
    def hide_adult_content(self) -> bool:
        return self.hide_adult.isChecked()
