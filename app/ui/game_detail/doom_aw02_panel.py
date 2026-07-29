"""Visible AW0.2 product slice for Doom Eternal."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton,
    QSpinBox, QTextEdit, QVBoxLayout,
)

from app.application.doom_vertical_slice import DoomDetailState, DoomVerticalSlice
from app.application.creator_sources import CreatorSourceBuilder
from app.application.journey_presentation import JourneyPresentationBuilder
from app.application.journey_templates import JourneyTemplateRegistry
from app.application.game_row_contracts import GameRowAction
from app.core.constants import ACCENT, SUCCESS, WARNING
from app.core.runtime import startup_storage
from velora_contracts.enums import CheckpointType
from app.ui.game_detail.journey_widgets import JourneyView


CHECKPOINT_LABELS = {
    "start": "Начало",
    "middle": "Середина",
    "end": "Финал",
}
STATUS_LABELS = {
    None: "НЕ НАЧИНАЛ",
    "planned": "ЗАПЛАНИРОВАНО",
    "playing": "ПРОХОЖУ",
    "completed": "ПРОШЁЛ",
    "abandoned": "БРОСИЛ",
}
ACTION_LABELS = {
    GameRowAction.START_PLAYTHROUGH: "Начать прохождение",
    GameRowAction.CONTINUE_PLAYTHROUGH: "Продолжить",
    GameRowAction.ADD_PLAYTIME: "Добавить время",
    GameRowAction.ADD_CHECKPOINT: "Контрольная точка",
    GameRowAction.ADD_IMPRESSION: "Впечатление",
    GameRowAction.RATE: "Оценить",
    GameRowAction.COMPLETE_PLAYTHROUGH: "Завершить",
}


class DoomAw02Panel(QFrame):
    """Self-contained Qt adapter; all persistence is delegated to services."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("doomAw02Panel")
        self.setStyleSheet(
            "QFrame#doomAw02Panel{background:#080E14;border:0;"
            "border-radius:9px;}"
        )
        self.slice: DoomVerticalSlice | None = None
        self.journey_builder = JourneyPresentationBuilder()
        self.template_registry = JourneyTemplateRegistry()
        self.creator_builder = CreatorSourceBuilder()
        self.creator_source_model = None
        storage = startup_storage()
        if storage is not None:
            self.slice = DoomVerticalSlice(storage.catalog_db, storage.user_db)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)
        title_row = QHBoxLayout()
        self.panel_title = QLabel("ЛИЧНЫЙ ПУТЬ")
        self.panel_title.setStyleSheet(
            "font-size:14pt;font-weight:750;color:white;"
        )
        title_row.addWidget(self.panel_title)
        title_row.addStretch()
        self.feedback = QLabel()
        self.feedback.setObjectName("muted")
        title_row.addWidget(self.feedback)
        self.primary_action = QPushButton()
        self.primary_action.setProperty("primary", True)
        self._primary_action_value = GameRowAction.START_PLAYTHROUGH
        self.primary_action.clicked.connect(
            lambda: self.run_action(self._primary_action_value)
        )
        title_row.addWidget(self.primary_action)
        self.playthrough_selector = QComboBox()
        self.playthrough_selector.setMinimumWidth(150)
        self.playthrough_selector.currentIndexChanged.connect(
            self._switch_playthrough
        )
        title_row.addWidget(self.playthrough_selector)
        self.actions_button = QPushButton("ДЕЙСТВИЯ")
        title_row.addWidget(self.actions_button)
        root.addLayout(title_row)

        summary = QHBoxLayout()
        summary.setSpacing(8)
        self.status = self._metric("СТАТУС")
        self.time = self._metric("ОБЩЕЕ ВРЕМЯ")
        self.run = self._metric("ПРОХОЖДЕНИЕ")
        self.rating = self._metric("МОЯ ОЦЕНКА")
        self.checkpoint = self._metric("ПРОГРЕСС")
        for card, _ in (self.status, self.time, self.run, self.rating, self.checkpoint):
            summary.addWidget(card, 1)
        root.addLayout(summary)

        self.journey_page = JourneyView()
        self.journey_page.quick_save_requested.connect(self._save_stage)
        root.addWidget(self.journey_page)

        footer = QHBoxLayout()
        footer.addStretch()
        self.footer_buttons: dict[GameRowAction, QPushButton] = {}
        for text, action in (
            ("ДОБАВИТЬ ВРЕМЯ", GameRowAction.ADD_PLAYTIME),
            ("КОНТРОЛЬНАЯ ТОЧКА", GameRowAction.ADD_CHECKPOINT),
            ("ВПЕЧАТЛЕНИЕ", GameRowAction.ADD_IMPRESSION),
            ("ОЦЕНИТЬ", GameRowAction.RATE),
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, value=action: self.run_action(value))
            self.footer_buttons[action] = button
            footer.addWidget(button)
        root.addLayout(footer)
        self.setVisible(False)

    @staticmethod
    def _metric(caption: str):
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#0B141C;border:0;border-radius:7px;}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(3)
        label = QLabel(caption)
        label.setObjectName("caption")
        value = QLabel("—")
        value.setStyleSheet("font-size:12pt;font-weight:700;color:white;border:0;")
        layout.addWidget(label)
        layout.addWidget(value)
        return card, value

    def refresh(self) -> None:
        if self.slice is None:
            self._error("Хранилище AW0.2 недоступно")
            return
        try:
            state = self.slice.load_detail()
        except Exception as exc:
            self._error(str(exc))
            return
        self.feedback.setText("")
        self._render(state)

    def _render(self, state: DoomDetailState) -> None:
        row = state.row
        self.panel_title.setText(f"{row.title} · ЛИЧНЫЙ ПУТЬ")
        current = state.playthroughs[-1] if state.playthroughs else None
        self.status[1].setText(STATUS_LABELS.get(row.playthrough_status, "НЕ НАЧИНАЛ"))
        self.time[1].setText(_duration(row.total_playtime_minutes))
        self.run[1].setText(f"№ {current.sequence_no}" if current else "—")
        self.rating[1].setText(
            f"{row.current_personal_rating_tenths / 10:.1f}"
            if row.current_personal_rating_tenths is not None else "—"
        )
        self.rating[1].setStyleSheet(
            f"font-size:12pt;font-weight:700;color:"
            f"{SUCCESS if (row.current_personal_rating_tenths or 0) >= 80 else WARNING};border:0;"
        )
        self.checkpoint[1].setText(
            CHECKPOINT_LABELS.get(row.current_checkpoint or "", "—")
        )
        selected_sequence = self.playthrough_selector.currentData()
        self.playthrough_selector.blockSignals(True)
        self.playthrough_selector.clear()
        for item in state.playthroughs:
            self.playthrough_selector.addItem(
                f"Прохождение №{item.sequence_no}", item.sequence_no
            )
        if not state.playthroughs:
            self.playthrough_selector.addItem("Новое прохождение", None)
        target = (
            selected_sequence
            if selected_sequence is not None
            else current.sequence_no if current else None
        )
        selector_index = self.playthrough_selector.findData(target)
        self.playthrough_selector.setCurrentIndex(max(0, selector_index))
        self.playthrough_selector.blockSignals(False)
        journey = self.journey_builder.build(
            state,
            self.template_registry.doom_eternal(),
            playthrough_sequence=self.playthrough_selector.currentData(),
        )
        self.journey_page.set_presentation(journey)
        self.journey_page.set_editable(
            current is None
            or self.playthrough_selector.currentData() == current.sequence_no
        )
        self.creator_source_model = self.creator_builder.build(journey)
        actions = tuple(action for action in state.actions if action is not GameRowAction.OPEN)
        self._configure_actions(actions)

    def _switch_playthrough(self) -> None:
        self.refresh()

    def _refresh_creator_sources(self) -> None:
        if self.slice is None:
            return
        try:
            state = self.slice.load_detail()
            journey = self.journey_builder.build(
                state, self.template_registry.doom_eternal()
            )
            self.creator_source_model = self.creator_builder.build(journey)
        except Exception:
            return

    def _configure_actions(self, actions: tuple[GameRowAction, ...]) -> None:
        preferred = (
            GameRowAction.START_PLAYTHROUGH
            if GameRowAction.START_PLAYTHROUGH in actions
            else GameRowAction.CONTINUE_PLAYTHROUGH
            if GameRowAction.CONTINUE_PLAYTHROUGH in actions
            else GameRowAction.RATE
        )
        self.primary_action.setText(
            "НАЧАТЬ ЗАНОВО"
            if preferred is GameRowAction.START_PLAYTHROUGH and self.run[1].text() != "—"
            else ACTION_LABELS.get(preferred, "ОЦЕНИТЬ").upper()
        )
        self._primary_action_value = preferred
        for action, button in self.footer_buttons.items():
            button.setVisible(action in actions)
        menu = QMenu(self.actions_button)
        for action in actions:
            item = menu.addAction(ACTION_LABELS.get(action, action.value))
            item.triggered.connect(
                lambda checked=False, value=action: self.run_action(value)
            )
        self.actions_button.setMenu(menu)

    def _save_stage(
        self,
        stage_id: str,
        status: str,
        rating: float | None,
        impression: str,
    ) -> None:
        """Persist the compact editor through the existing AW0.2 services."""
        if self.slice is None:
            return
        try:
            requested_status = {
                "planned": "НЕ НАЧИНАЛ",
                "playing": "ПРОХОЖУ",
                "completed": "ПРОШЁЛ",
                "abandoned": "БРОСИЛ",
            }[status]
            stage_number = max(1, int(stage_id.rsplit("-", 1)[-1]))
            stage_titles = self.template_registry.doom_eternal().stage_titles
            stage_title = stage_titles[min(stage_number - 1, len(stage_titles) - 1)]
            # Completing a mission is not the same as completing the entire
            # playthrough.  Schema 1 stores playthrough status and milestone
            # checkpoints separately, so only the final mission closes a run.
            status_value = (
                "ПРОХОЖУ"
                if status == "completed" and stage_number < len(stage_titles)
                else requested_status
            )
            self.slice.set_status(status_value)
            checkpoint = (
                CheckpointType.START
                if stage_number == 1
                else CheckpointType.END
                if stage_number == len(stage_titles)
                else CheckpointType.MIDDLE
            )
            if rating is not None or status == "completed":
                self.slice.save_checkpoint(
                    checkpoint,
                    title=stage_title,
                    rating=rating,
                )
            if impression:
                # A Journey can contain many stages while Schema 1 deliberately
                # permits only one impression for each coarse checkpoint.
                # Store stage impressions as progress-bound notes instead of
                # forcing 13 stages into start/middle/end.
                self.slice.add_impression(
                    impression,
                    None,
                    progress_value=float(stage_number),
                    progress_unit="journey_stage",
                )
            self.feedback.setStyleSheet(f"color:{SUCCESS};")
            self.feedback.setText("Этап сохранён")
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def run_action(self, action: GameRowAction) -> None:
        if self.slice is None:
            return
        try:
            if action in (GameRowAction.START_PLAYTHROUGH, GameRowAction.CONTINUE_PLAYTHROUGH):
                self.slice.set_status("ПРОХОЖУ")
            elif action is GameRowAction.ADD_PLAYTIME:
                value = request_playtime(self)
                if value:
                    self.slice.add_playtime(*value)
            elif action is GameRowAction.ADD_CHECKPOINT:
                state = self.slice.load_detail()
                value = request_checkpoint(
                    self, state.row.total_playtime_minutes
                )
                if value:
                    self.slice.save_checkpoint(**value)
            elif action is GameRowAction.ADD_IMPRESSION:
                value = request_impression(self)
                if value:
                    self.slice.add_impression(*value)
            elif action is GameRowAction.RATE:
                value = request_personal_rating(self)
                if value:
                    self.slice.save_personal_rating(*value)
            elif action is GameRowAction.COMPLETE_PLAYTHROUGH:
                self.slice.set_status("ПРОШЁЛ")
            self.feedback.setStyleSheet(f"color:{SUCCESS};")
            self.feedback.setText("Сохранено")
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _error(self, message: str) -> None:
        self.feedback.setStyleSheet("color:#FF625C;")
        self.feedback.setText("Ошибка сохранения")
        QMessageBox.warning(self, "Doom Eternal · AW0.2", message)


def request_playtime(parent=None) -> tuple[int, int] | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Добавить игровое время")
    form = QFormLayout(dialog)
    hours, minutes = QSpinBox(), QSpinBox()
    hours.setRange(0, 9999)
    minutes.setRange(0, 59)
    form.addRow("Часы", hours)
    form.addRow("Минуты", minutes)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    return (hours.value(), minutes.value()) if dialog.exec() else None


def request_checkpoint(parent=None, accumulated_minutes: int = 0) -> dict | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Контрольная точка")
    form = QFormLayout(dialog)
    stage = QComboBox()
    for value, label in CHECKPOINT_LABELS.items():
        stage.addItem(label, value)
    title = QTextEdit()
    title.setMaximumHeight(48)
    description = QTextEdit()
    description.setMaximumHeight(90)
    date = QDateTimeEdit(QDateTime.currentDateTime())
    date.setEnabled(False)
    rating = QDoubleSpinBox()
    rating.setRange(0.0, 10.0)
    rating.setDecimals(1)
    rating.setSpecialValueText("Без оценки")
    form.addRow("Этап", stage)
    form.addRow("Название", title)
    form.addRow("Краткое описание", description)
    form.addRow("Дата", date)
    form.addRow("Накопленное время", QLabel(_duration(accumulated_minutes)))
    form.addRow("Промежуточная оценка", rating)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if not dialog.exec():
        return None
    value = rating.value()
    return {
        "checkpoint": CheckpointType(stage.currentData()),
        "title": title.toPlainText(),
        "description": description.toPlainText(),
        "rating": value if value > 0 else None,
    }


def request_impression(parent=None) -> tuple[str, CheckpointType | None] | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Новое впечатление")
    form = QFormLayout(dialog)
    text = QTextEdit()
    text.setMinimumHeight(130)
    checkpoint = QComboBox()
    checkpoint.addItem("Без привязки", None)
    for value, label in CHECKPOINT_LABELS.items():
        checkpoint.addItem(label, value)
    form.addRow("Текст впечатления", text)
    form.addRow("Контрольная точка", checkpoint)
    form.addRow("Дата", QLabel(datetime.now().strftime("%d.%m.%Y %H:%M")))
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if not dialog.exec() or not text.toPlainText().strip():
        return None
    value = checkpoint.currentData()
    return (
        text.toPlainText().strip(),
        CheckpointType(value) if value else None,
    )


def request_personal_rating(parent=None) -> tuple[float, str] | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Личная оценка Doom Eternal")
    form = QFormLayout(dialog)
    rating = QDoubleSpinBox()
    rating.setRange(0.1, 10.0)
    rating.setSingleStep(0.1)
    rating.setDecimals(1)
    rating.setValue(8.0)
    review = QTextEdit()
    review.setMaximumHeight(100)
    form.addRow("Оценка", rating)
    form.addRow("Комментарий", review)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    return (rating.value(), review.toPlainText()) if dialog.exec() else None


def _duration(minutes: int) -> str:
    return f"{minutes // 60} ч {minutes % 60:02d} мин" if minutes else "—"


def _rating(value: int | None) -> str:
    return f"{value / 10:.1f}" if value is not None else "—"


def _date(value: str | None) -> str:
    return _date_time(value).split(" ")[0] if value else "—"


def _date_time(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value
