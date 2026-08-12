from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.core.constants import APP_VERSION, BASE_RELEASE, CATALOG_VERSION
from app.ui.velora_ui.icons import IconProvider


VELORA_GITHUB_URL = "https://github.com/Velora-Desktop/Velora"


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О проекте Velora")
        self.setWindowIcon(IconProvider.icon("animated.info", 20))
        self.setModal(True); self.setMinimumSize(600, 390)
        root = QVBoxLayout(self)
        heading = QHBoxLayout()
        title = QPushButton("VELORA")
        title.setObjectName("aboutProjectLink")
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setToolTip("Открыть Velora на GitHub")
        title.setStyleSheet(
            "QPushButton#aboutProjectLink{font-family:Georgia;font-size:24pt;"
            "font-weight:600;color:#F3F0F7;background:transparent;border:0;"
            "padding:0;text-align:left;}"
            "QPushButton#aboutProjectLink:hover{color:#B45CFF;background:transparent;"
            "border:0;}"
            "QPushButton#aboutProjectLink:pressed{color:#8D32DD;background:transparent;"
            "border:0;}"
        )
        title.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(VELORA_GITHUB_URL))
        )
        heading.addWidget(title); heading.addStretch(); root.addLayout(heading)
        intro = QLabel(
            "Velora — open-source инструментарий для личной медиатеки, оценок и истории впечатлений.\n\n"
            "Личные оценки, история, время, категории и настройки хранятся только локально на компьютере пользователя. "
            "Velora не отправляет пользовательские данные на внешние серверы."
        )
        intro.setWordWrap(True); root.addWidget(intro); root.addStretch()
        attribution = QLabel(
            'Иконки: <a href="https://www.flaticon.com/uicons">Flaticon</a> · '
            '<a href="https://icons8.com">Icons8</a><br>'
            'Логотипы компаний: <a href="https://commons.wikimedia.org/">Wikimedia Commons</a>. '
            'Источники отдельных файлов указаны в локальном manifest.'
        )
        attribution.setOpenExternalLinks(True); attribution.setTextInteractionFlags(attribution.textInteractionFlags())
        root.addWidget(attribution)
        credits = QLabel(
            f"Автор: Станислав Смирнов\n"
            f"Разработчик: Станислав Смирнов\n"
            f"Версия: {APP_VERSION} — Alpha Windows\n"
            f"Базовый релиз: {BASE_RELEASE}\n"
            f"Текущий каталог: {CATALOG_VERSION}\n"
            "Схема профиля: 1"
        )
        credits.setStyleSheet("color:#C9A7FF;font-weight:500;"); root.addWidget(credits)
