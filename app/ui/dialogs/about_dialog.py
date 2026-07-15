from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from app.core.icon_registry import IconRegistry


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О проекте Velora")
        self.setWindowIcon(IconRegistry.icon("info", variant="dark", category="feedback"))
        self.setModal(True); self.setMinimumSize(600, 390)
        root = QVBoxLayout(self)
        heading = QHBoxLayout(); icon = QLabel(); icon.setPixmap(IconRegistry.pixmap("info", 24, variant="dark", category="feedback")); heading.addWidget(icon)
        title = QLabel("VELORA"); title.setStyleSheet("font-family:Georgia;font-size:24pt;font-weight:600;"); heading.addWidget(title); heading.addStretch(); root.addLayout(heading)
        intro = QLabel(
            "Velora — open-source инструментарий для личной медиатеки, оценок и истории впечатлений.\n\n"
            "Личные оценки, история, время, категории и настройки хранятся только локально на компьютере пользователя. "
            "Velora не отправляет пользовательские данные на внешние серверы."
        )
        intro.setWordWrap(True); root.addWidget(intro); root.addStretch()
        attribution = QLabel('Uicons от <a href="https://www.flaticon.com/uicons">Flaticon</a>')
        attribution.setOpenExternalLinks(True); attribution.setTextInteractionFlags(attribution.textInteractionFlags())
        root.addWidget(attribution)
        credits = QLabel("Автор: Станислав Смирнов\nРазработчик: Станислав Смирнов\nВерсия: AW0.07 — Alpha Windows\nКаталог: AW0.0711")
        credits.setStyleSheet("color:#C9A7FF;font-weight:500;"); root.addWidget(credits)
