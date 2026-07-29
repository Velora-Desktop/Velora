"""Creator preview backed by the AW0.21 Creator Source Model."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.application.creator_sources import CreatorSourceBuilder
from app.application.doom_vertical_slice import DoomVerticalSlice
from app.application.journey_presentation import JourneyPresentationBuilder
from app.application.journey_templates import JourneyTemplateRegistry
from app.core.runtime import startup_storage


class CreatorPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 24)
        root.setSpacing(14)
        title = QLabel("Creator")
        title.setStyleSheet("font-size:24pt;font-weight:700;")
        root.addWidget(title)
        intro = QLabel(
            "Отмечайте впечатления и ключевые моменты в Journey — "
            "они появятся здесь как материал для будущего сценария."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.context = QLabel()
        self.context.setStyleSheet(
            "background:#0B141C;border:1px solid #2B3944;border-radius:8px;"
            "padding:14px;font-size:11pt;"
        )
        self.context.setWordWrap(True)
        root.addWidget(self.context)
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        root.addLayout(self.grid, 1)

        actions = QHBoxLayout()
        for text in ("СОБРАТЬ СЦЕНАРИЙ", "ЭКСПОРТ DOCX", "ЭКСПОРТ TXT"):
            button = QPushButton(text)
            button.setEnabled(False)
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)
        status = QLabel("Journey Sources доступны для предпросмотра · редактор Creator появится позже")
        status.setAlignment(Qt.AlignmentFlag.AlignRight)
        status.setStyleSheet("color:#9A82B7;")
        root.addWidget(status)
        self.refresh()

    def refresh(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        storage = startup_storage()
        if storage is None:
            self.context.setText("Источник данных AW0.2 пока недоступен.")
            return
        try:
            state = DoomVerticalSlice(storage.catalog_db, storage.user_db).load_detail()
            journey = JourneyPresentationBuilder().build(
                state, JourneyTemplateRegistry().doom_eternal()
            )
            model = CreatorSourceBuilder().build(journey)
        except Exception as exc:
            self.context.setText(f"Creator Source Preview временно недоступен: {exc}")
            return
        categories: dict[str, int] = {}
        for source in model.sources:
            categories[source.source_type] = categories.get(source.source_type, 0) + 1
        self.context.setText(
            f"<b>{model.game_title}</b> · прохождение №{journey.playthrough_sequence or 1}<br>"
            f"Доступно источников: {len(model.sources)} · "
            f"отмечено: {len(model.selected_sources)} · "
            f"шаблон: {model.journey_type}"
        )
        cards = [
            ("GAME", model.game_title),
            ("JOURNEY SOURCES", ", ".join(f"{key}: {value}" for key, value in categories.items()) or "Пока пусто"),
            ("ВЫБРАННЫЕ МАТЕРИАЛЫ", "\n".join(
                f"• {item.title}" for item in model.selected_sources[-4:]
            ) or "Отметьте материал в Journey"),
            ("OUTLINE", "Будет собран из выбранных источников"),
            ("SCRIPT", "Редактор сценария появится в следующем этапе"),
            ("FOOTAGE / EXPORT", "Подготовлено место для будущего рабочего процесса"),
        ]
        for index, (heading, text) in enumerate(cards):
            card = QFrame()
            card.setObjectName("creatorSourceCard")
            card.setStyleSheet(
                "QFrame#creatorSourceCard{background:#0B141C;"
                "border:1px solid #263640;border-radius:8px;}"
            )
            layout = QVBoxLayout(card)
            label = QLabel(heading)
            label.setStyleSheet("font-weight:700;color:#C998FF;")
            layout.addWidget(label)
            detail = QLabel(text)
            detail.setObjectName("muted")
            detail.setWordWrap(True)
            layout.addWidget(detail)
            layout.addStretch()
            self.grid.addWidget(card, index // 3, index % 3)
