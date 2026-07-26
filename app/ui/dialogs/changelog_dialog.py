from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.icon_registry import IconRegistry
from app.data.catalog_repository import CATALOG_DB
from app.services.catalog_update_service import CatalogUpdateService


MAJOR_CHANGELOG = """AW0.09 — новый цикл разработки

• Добавлены локальные пользовательские разделы, категории, подкатегории и карточки.
• Официальные и пользовательские разделы объединены в прокручиваемую верхнюю навигацию.
• Исправлены вылеты после создания, удаления и переключения пользовательских разделов.
• Добавлены умная библиотека, очередь, цели, теги, заметки и локальный помощник выбора.
• Профиль «Мой Velora» получил обзор, статистику, избранное и историю активности.
• Расширены карточки игр, фильмов, сериалов и программ.
• Каталог доведён до 400 карточек — по 100 объектов каждого основного типа.
• Добавлены официальные обложки, русские описания и профессиональные источники оценок.
• В Studio добавлен главный источник оценки: по умолчанию Metacritic, если он доступен.
• Главный источник даёт 50% итоговой оценки, остальные источники делят вторую половину.
• Главный источник можно изменить в Studio отдельно для каждой карточки.
"""


def catalog_changelog_text() -> str:
    history = CatalogUpdateService.history(CATALOG_DB)
    if not history:
        return "ОБЩАЯ ВЕРСИЯ КАТАЛОГА AW0.099\n\nИстория микропатчей пока отсутствует."
    type_order = ("Игры", "Фильмы", "Сериалы", "Программы")
    blocks = []
    for change in reversed(history):
        additions = [
            f"+{change.added[name]} {name.lower()}"
            for name in type_order
            if change.added.get(name)
        ]
        additions.extend(
            f"+{count} {name.lower()}"
            for name, count in change.added.items()
            if name not in type_order and count
        )
        details = additions or ["без новых объектов"]
        if change.updated:
            details.append(f"обновлено карточек: {change.updated}")
        if change.removed:
            details.append(f"удалено карточек: {change.removed}")
        blocks.append(f"{change.version}\n" + " · ".join(details))
    return "ОБЩАЯ ВЕРСИЯ КАТАЛОГА AW0.099\n\n" + "\n\n".join(blocks)


class ChangelogDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История изменений Velora")
        self.setWindowIcon(IconRegistry.icon("history_recent", variant="dark", category="ui"))
        self.setModal(True)
        self.setMinimumSize(820, 580)

        root = QVBoxLayout(self)
        title = QLabel("ИСТОРИЯ ИЗМЕНЕНИЙ")
        title.setStyleSheet("font-size:16pt; font-weight:600;")
        root.addWidget(title)

        content = QWidget()
        columns = QHBoxLayout(content)
        columns.setSpacing(14)

        catalog_column = QVBoxLayout()
        catalog_title = QLabel("МИКРОПАТЧИ КАТАЛОГА")
        catalog_title.setStyleSheet("font-size:12pt;font-weight:700;color:#CFA1FF;")
        catalog_column.addWidget(catalog_title)
        catalog_changes = QLabel(catalog_changelog_text())
        catalog_changes.setWordWrap(True)
        catalog_changes.setStyleSheet(
            "background:#0B141C;border:1px solid #2D3A44;"
            "border-radius:8px;padding:14px;color:#CFA1FF;"
        )
        catalog_column.addWidget(catalog_changes)
        catalog_column.addStretch()
        columns.addLayout(catalog_column, 2)

        program_column = QVBoxLayout()
        program_title = QLabel("КРУПНЫЕ ИЗМЕНЕНИЯ AW0.09")
        program_title.setStyleSheet("font-size:12pt;font-weight:700;color:#F0F1F4;")
        program_column.addWidget(program_title)
        changes = QLabel(MAJOR_CHANGELOG)
        changes.setWordWrap(True)
        program_column.addWidget(changes)
        program_column.addStretch()
        columns.addLayout(program_column, 3)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
