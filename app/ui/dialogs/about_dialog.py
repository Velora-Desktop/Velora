from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О проекте Velora")
        self.setModal(True)
        self.setMinimumSize(600, 390)
        root = QVBoxLayout(self)
        title = QLabel("VELORA")
        title.setStyleSheet("font-family:Georgia; font-size:24pt; font-weight:600;")
        root.addWidget(title)

        intro = QLabel(
            "Velora — open-source инструментарий, созданный для людей.\n\n"
            "Приложение помогает собирать личный каталог игр и других произведений, "
            "оценивать их по понятным критериям, сохранять историю впечатлений и "
            "организовывать собственное пространство без обязательной регистрации.\n\n"
            "Velora уважает выбор пользователя: личные оценки, история, настройки и "
            "созданные категории принадлежат пользователю и не должны теряться при обновлениях.\n\n"
            "Velora не хранит пользовательские данные на внешних серверах. Оценки, история, "
            "игровое время, категории и настройки сохраняются локально на компьютере пользователя. "
            "Такой подход снижает зависимость от сторонних сервисов и помогает сохранить контроль "
            "над личными данными."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)
        root.addStretch()
        credits = QLabel(
            "Автор: Станислав Смирнов\n"
            "Разработчик: Станислав Смирнов\n"
            "Версия: AW0.04 — Alpha Windows"
        )
        credits.setStyleSheet("color:#C9A7FF; font-weight:500;")
        root.addWidget(credits)
