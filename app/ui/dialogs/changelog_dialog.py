from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


class ChangelogDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История изменений Velora")
        self.setModal(True)
        self.setMinimumSize(560, 380)
        root = QVBoxLayout(self)
        title = QLabel("ИСТОРИЯ ИЗМЕНЕНИЙ")
        title.setStyleSheet("font-size:16pt; font-weight:600;")
        root.addWidget(title)
        changes = QLabel(
            "AW0.03\n"
            "• подключена официальная SQLite-база каталога с постоянными читаемыми ID;\n"
            "• добавлена интеграция с редактором Velora Studio 0.01;\n"
            "• официальный каталог отделён от будущих пользовательских оценок и карточек.\n\n"
            "AW0.02\n"
            "• переработан интерфейс по второму концепту;\n"
            "• добавлены рабочие фильтры и сортировки;\n"
            "• добавлены статусы, оценивание и хронология времени;\n"
            "• добавлена фильтрация контента 18+.\n\n"
            "AW0.01\n"
            "• создан первый модульный каркас Velora;\n"
            "• опубликован ранний снимок разработки."
        )
        changes.setWordWrap(True)
        root.addWidget(changes)
        root.addStretch()
