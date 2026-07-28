from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.icon_registry import IconRegistry
from app.data.catalog_repository import CATALOG_DB
from app.services.catalog_update_service import CatalogChange, CatalogUpdateService


PATCH_NOTES = {
    "AW0.0101": (
        "Добавлены официальные обложки Apex Legends, BioShock, BioShock Infinite, "
        "Control и Counter-Strike 2."
    ),
    "AW0.062": "Расширен официальный каталог и обновлены базовые карточки.",
    "AW0.063": "Обновлена структура и метаданные 40 карточек.",
    "AW0.064": "Техническая подготовка каталога.",
    "AW0.065": "Унифицированы данные 40 карточек.",
    "AW0.066": "Синхронизированы типы контента и поля 40 карточек.",
    "AW0.067": "Технический микропатч структуры.",
    "AW0.068": "Обновлены сведения 10 карточек.",
    "AW0.071": "Расширен тестовый каталог.",
    "AW0.0711": "Добавлена карточка и исправлена совместимость каталога.",
    "AW0.0712": "Исправлена одна карточка каталога.",
    "AW0.091": "Добавлено по 10 карточек каждого основного типа.",
    "AW0.092": "Каталог расширен до 400 объектов.",
    "AW0.093": "Карточки дополнены описаниями и структурированными сведениями.",
    "AW0.094": "Добавлены пять официальных обложек.",
    "AW0.097": "Русские описания применены ко всему каталогу.",
    "AW0.098": "Нормализованы профессиональные источники оценок.",
    "AW0.099": "Исправлены источники и оценки Doom Eternal.",
    "AW0.0991": (
        "Подтверждены профессиональные оценки и пересчитаны их средние значения; "
        "Borderlands 2 дополнен оценками, "
        "PC Gamer унифицирован в 39 карточках, а дубли 7-Zip, Audacity "
        "и Bitwarden объединены."
    ),
}

MAJOR_GROUPS = (
    (
        "ИНТЕРФЕЙС И UX",
        (
            "<b>Единая прокручиваемая навигация</b> для официальных и пользовательских разделов.",
            "Независимая сортировка внутри каждой подгруппы каталога.",
            "Переработаны Quick View, подробные карточки и профиль «Мой Velora».",
        ),
    ),
    (
        "ГРАФИКА И РЕСУРСЫ",
        (
            "<b>Подключён централизованный IconRegistry</b> и единый набор SVG-иконок.",
            "Добавлены официальные обложки и согласован формат 2:3.",
            "Унифицированы состояния наведения, выделения и цветовые акценты.",
        ),
    ),
    (
        "ДВИЖОК И АРХИТЕКТУРА",
        (
            "<b>Официальный каталог и пользовательские данные разделены</b> между catalog.db и user.db.",
            "Добавлены миграции пользовательской базы, сервисы аналитики и резервного копирования.",
            "Стабильные catalog_id открывают одну карточку из каталога, профиля и избранного.",
        ),
    ),
    (
        "КАТАЛОГ И ДАННЫЕ",
        (
            "<b>Каталог был расширен до 400 записей</b>; после объединения трёх дублей "
            "содержит 397 уникальных карточек.",
            "Добавлены русские описания и профессиональные источники оценок.",
            "Итоговая оценка вычисляется как среднее всех заполненных профессиональных источников.",
        ),
    ),
    (
        "ЛИЧНАЯ БИБЛИОТЕКА",
        (
            "<b>Добавлены локальные разделы, категории, подкатегории и карточки.</b>",
            "Реализованы очередь, цели, теги, заметки и локальный помощник выбора.",
            "Профиль получил обзор, статистику, избранное и историю активности.",
        ),
    ),
    (
        "СТАБИЛЬНОСТЬ",
        (
            "<b>Исправлены вылеты</b> после создания, удаления и переключения пользовательских разделов.",
            "Добавлены проверки миграций, целостности каталога и безопасное восстановление.",
            "Пользовательские оценки и история не изменяются микропатчами каталога.",
        ),
    ),
)

CURRENT_CYCLE_GROUPS = (
    (
        "ИНТЕРФЕЙС И UX",
        (
            "<b>Переработано окно истории изменений:</b> крупные циклы и "
            "микропатчи каталога больше не перекрывают друг друга.",
            "Микропатчи перенесены в отдельную правую колонку с собственной прокруткой.",
        ),
    ),
    (
        "КАТАЛОГ",
        (
            "<b>Минимальный размер страницы увеличен до 50 объектов.</b>",
            "Доступны ступени пагинации: 50, 100, 200 и 500 карточек.",
        ),
    ),
    (
        "СТАБИЛЬНОСТЬ ПЕРЕХОДОВ",
        (
            "<b>Исправлены вылеты при повторном открытии карточек</b> игр, "
            "фильмов, сериалов и программ.",
            "Восстановлена последовательность: клик по строке открывает Quick View, "
            "а клик по его информационной области — полную страницу.",
            "Устранена лишняя перестройка каталога во время обработки клика и "
            "добавлена поддержка разных форматов актёрского состава.",
            "Объединены дубли 7-Zip, Audacity и Bitwarden без потери наиболее "
            "полных сведений и профессиональных оценок.",
        ),
    ),
)

MAJOR_RELEASE_HISTORY = (
    (
        "AW0.08",
        "Публичная альфа: устойчивый слой данных, первый запуск, профиль, "
        "фильтрация 18+ и обслуживание локальной библиотеки.",
    ),
    (
        "AW0.07",
        "Визуальная полировка каталога, IconRegistry, единая сетка строк, "
        "расширенная статистика и подготовка Studio к пакетной публикации.",
    ),
    (
        "AW0.06",
        "Игры, фильмы, сериалы и программы объединены общей моделью каталога; "
        "добавлены сервисы, миграции и глобальный поиск.",
    ),
    (
        "AW0.05",
        "Переработаны профиль «Мой Velora», подробные карточки, личные оценки, "
        "избранное и аналитика.",
    ),
    (
        "AW0.04",
        "История взаимодействий вынесена в user_activity, время хранится числом, "
        "а Quick View разделён на самостоятельные компоненты.",
    ),
    (
        "AW0.03",
        "Подключены SQLite-каталог и стабильные понятные ID; создана Velora Studio "
        "для редактирования официальной базы.",
    ),
    (
        "AW0.02",
        "Основной интерфейс приведён к утверждённому концепту: каталог, сортировка, "
        "статусы, Quick View и навигация.",
    ),
    (
        "AW0.01",
        "Создан первый модульный PySide6-каркас Velora с навигацией, каталогом и "
        "едиными диалогами-заглушками.",
    ),
)


def _addition_text(change: CatalogChange) -> str:
    canonical = ("Игры", "Фильмы", "Сериалы", "Программы")
    values = list(change.added.items())
    if not values:
        return ""
    if all(name in canonical for name, _ in values):
        parts = [f"+{count} {name.lower()}" for name, count in values if count]
    elif len(values) == 4:
        parts = [
            f"+{count} {canonical[index].lower()}"
            for index, (_, count) in enumerate(values)
            if count
        ]
    else:
        total = sum(count for _, count in values)
        parts = [f"+{total} объектов"] if total else []
    return " · ".join(parts)


def _patch_html(change: CatalogChange) -> str:
    details = []
    additions = _addition_text(change)
    if additions:
        details.append(additions)
    if change.updated:
        details.append(f"обновлено карточек: {change.updated}")
    if change.removed:
        details.append(f"удалено карточек: {change.removed}")
    details_text = " · ".join(details) if details else "без изменения количества карточек"
    note = PATCH_NOTES.get(change.version, "Обновление официального каталога.")
    date = change.published_at[:10] if change.published_at else ""
    date_html = f" <span style='color:#697989'>· {escape(date)}</span>" if date else ""
    return (
        "<div style='margin-bottom:14px'>"
        f"<b style='color:#CFA1FF'>{escape(change.version)}</b>{date_html}<br>"
        f"<span style='color:#E7EAF0'>{escape(note)}</span><br>"
        f"<span style='color:#91A1B2'>{escape(details_text)}</span>"
        "</div>"
    )


def catalog_changelog_html() -> str:
    history = CatalogUpdateService.history(CATALOG_DB)
    if not history:
        return (
            "<b>ОБЩАЯ ВЕРСИЯ КАТАЛОГА AW0.0101</b><br><br>"
            "<span style='color:#91A1B2'>История микропатчей пока отсутствует.</span>"
        )
    patches = "".join(_patch_html(change) for change in reversed(history))
    return "<b>ОБЩАЯ ВЕРСИЯ КАТАЛОГА AW0.0101</b><br><br>" + patches


def _scrollable(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    return scroll


def _major_card(title: str, entries: tuple[str, ...]) -> QFrame:
    card = QFrame()
    card.setObjectName("changelogCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(7)
    heading = QLabel(title)
    heading.setStyleSheet("font-size:11pt;font-weight:700;color:#CFA1FF;")
    layout.addWidget(heading)
    body = QLabel("<br>".join(f"• {entry}" for entry in entries))
    body.setTextFormat(Qt.TextFormat.RichText)
    body.setWordWrap(True)
    body.setStyleSheet("color:#DCE2E9;line-height:1.3;")
    layout.addWidget(body)
    return card


def _release_history_card() -> QFrame:
    card = QFrame()
    card.setObjectName("changelogCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)
    heading = QLabel("ПРОШЛЫЕ ЦИКЛЫ РАЗРАБОТКИ")
    heading.setStyleSheet("font-size:11pt;font-weight:700;color:#CFA1FF;")
    layout.addWidget(heading)
    for version, description in MAJOR_RELEASE_HISTORY:
        label = QLabel(
            f"<b style='color:#F1F2F4'>{escape(version)}</b><br>"
            f"<span style='color:#AAB5C0'>{escape(description)}</span>"
        )
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        layout.addWidget(label)
    return card


class ChangelogDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История изменений Velora")
        self.setWindowIcon(IconRegistry.icon("history_recent", variant="dark", category="ui"))
        self.setModal(True)
        self.resize(1120, 720)
        self.setMinimumSize(860, 580)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(12)

        title = QLabel("ИСТОРИЯ ИЗМЕНЕНИЙ")
        title.setStyleSheet("font-size:16pt;font-weight:700;")
        root.addWidget(title)

        cycle = QLabel(
            "<b>AW0.10 — НОВЫЙ ЦИКЛ РАЗРАБОТКИ</b><br>"
            "<span style='color:#91A1B2'>Цикл открыт после завершения AW0.09. "
            "Новые изменения будут фиксироваться здесь отдельно от микропатчей каталога.</span>"
        )
        cycle.setTextFormat(Qt.TextFormat.RichText)
        cycle.setWordWrap(True)
        cycle.setStyleSheet(
            "background:#131022;border:1px solid #6E24B6;"
            "border-radius:8px;padding:12px;color:#F1E7FF;"
        )
        root.addWidget(cycle)

        columns = QHBoxLayout()
        columns.setSpacing(14)

        major_widget = QWidget()
        major_layout = QVBoxLayout(major_widget)
        major_layout.setContentsMargins(0, 0, 4, 0)
        current_title = QLabel("КРУПНЫЕ ИЗМЕНЕНИЯ AW0.10")
        current_title.setStyleSheet("font-size:12pt;font-weight:800;color:#F0F1F4;")
        major_layout.addWidget(current_title)
        current_grid = QGridLayout()
        current_grid.setSpacing(10)
        for index, (heading, entries) in enumerate(CURRENT_CYCLE_GROUPS):
            current_grid.addWidget(_major_card(heading, entries), index // 2, index % 2)
        major_layout.addLayout(current_grid)

        major_title = QLabel("КРУПНЫЕ ИЗМЕНЕНИЯ AW0.09")
        major_title.setStyleSheet("font-size:12pt;font-weight:800;color:#F0F1F4;")
        major_layout.addSpacing(8)
        major_layout.addWidget(major_title)
        grid = QGridLayout()
        grid.setSpacing(10)
        for index, (heading, entries) in enumerate(MAJOR_GROUPS):
            grid.addWidget(_major_card(heading, entries), index // 2, index % 2)
        major_layout.addLayout(grid)
        major_layout.addWidget(_release_history_card())
        major_layout.addStretch()
        columns.addWidget(_scrollable(major_widget), 3)

        patch_widget = QWidget()
        patch_layout = QVBoxLayout(patch_widget)
        patch_layout.setContentsMargins(4, 0, 0, 0)
        patch_title = QLabel("МИКРОПАТЧИ КАТАЛОГА")
        patch_title.setStyleSheet("font-size:12pt;font-weight:800;color:#CFA1FF;")
        patch_layout.addWidget(patch_title)
        patch_list = QLabel(catalog_changelog_html())
        patch_list.setTextFormat(Qt.TextFormat.RichText)
        patch_list.setWordWrap(True)
        patch_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        patch_list.setStyleSheet(
            "background:#0B141C;border:1px solid #2D3A44;"
            "border-radius:8px;padding:14px;color:#CFA1FF;"
        )
        patch_layout.addWidget(patch_list)
        patch_layout.addStretch()
        columns.addWidget(_scrollable(patch_widget), 2)

        root.addLayout(columns, 1)
        self.setStyleSheet(
            self.styleSheet()
            + "QFrame#changelogCard{background:#0B141C;border:1px solid #2D3A44;"
            "border-radius:8px;}"
        )
