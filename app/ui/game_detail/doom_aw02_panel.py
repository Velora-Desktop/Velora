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
            "QFrame#doomAw02Panel{background:transparent;border:0;}"
        )
        self.slice: DoomVerticalSlice | None = None
        self.journey_builder = JourneyPresentationBuilder()
        self.template_registry = JourneyTemplateRegistry()
        self.creator_builder = CreatorSourceBuilder()
        self.creator_source_model = None
        self.selected_playthrough_id: str | None = None
        storage = startup_storage()
        if storage is not None:
            self.slice = DoomVerticalSlice(storage.catalog_db, storage.user_db)

        root = QVBoxLayout(self)
        # The parent tab already provides the common 12 px content inset used
        # by both "About" and "Journey".  A second inset here made Journey
        # start lower and exposed the panel background as a dark rectangle.
        root.setContentsMargins(0, 0, 0, 0)
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
        self.journey_page.new_playthrough_requested.connect(
            self._create_playthrough
        )
        self.journey_page.playthrough_selection_requested.connect(
            self._select_journey_playthrough
        )
        self.journey_page.playthrough_delete_requested.connect(
            self._request_delete_playthrough
        )
        self.journey_page.stage_state_requested.connect(self._set_stage_state)
        self.journey_page.stage_rating_requested.connect(self._set_stage_rating)
        self.journey_page.entry_requested.connect(self._save_journey_entry)
        self.journey_page.event_revision_requested.connect(self._revise_journey_entry)
        self.journey_page.event_delete_requested.connect(self._delete_journey_entry)
        self.journey_page.stage_favorite_requested.connect(
            self._set_stage_favorite
        )
        self.journey_page.stage_media_requested.connect(self._set_stage_media)
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
        # AW0.23 Journey owns the playthrough summary and primary controls.
        for card, _value in (
            self.status, self.time, self.run, self.rating, self.checkpoint,
        ):
            card.setVisible(False)
        self.panel_title.setVisible(False)
        self.primary_action.setVisible(False)
        self.playthrough_selector.setVisible(False)
        self.actions_button.setVisible(False)
        for button in self.footer_buttons.values():
            button.setVisible(False)
        # Hidden AW0.2 compatibility controls must not remain as layout items:
        # QBoxLayout still reserves inter-item spacing for empty child layouts.
        # Journey is the sole visible workspace in AW0.23, so it receives the
        # complete panel height and starts at the same inset as "About".
        root.removeItem(title_row)
        root.removeItem(summary)
        root.removeItem(footer)
        root.setStretchFactor(self.journey_page, 1)

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
        current = next(
            (
                item for item in state.playthroughs
                if item.playthrough_id == row.current_playthrough_id
            ),
            state.playthroughs[-1] if state.playthroughs else None,
        )
        self.status[1].setText(STATUS_LABELS.get(row.playthrough_status, "НЕ НАЧИНАЛ"))
        self.time[1].setText(_duration(row.total_playtime_minutes))
        current_display_number = next(
            (
                index for index, item in enumerate(state.playthroughs, 1)
                if current is not None and item.playthrough_id == current.playthrough_id
            ),
            None,
        )
        self.run[1].setText(
            f"№ {current_display_number}" if current_display_number is not None else "—"
        )
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
        selected_id = self.selected_playthrough_id
        self.playthrough_selector.blockSignals(True)
        self.playthrough_selector.clear()
        for display_number, item in enumerate(state.playthroughs, 1):
            self.playthrough_selector.addItem(
                f"Прохождение №{display_number}", item.playthrough_id
            )
        if not state.playthroughs:
            self.playthrough_selector.addItem("Новое прохождение", None)
        available_ids = {item.playthrough_id for item in state.playthroughs}
        target = (
            selected_id
            if selected_id in available_ids
            else current.playthrough_id if current is not None
            else state.playthroughs[-1].playthrough_id if state.playthroughs
            else None
        )
        self.selected_playthrough_id = target
        selector_index = self.playthrough_selector.findData(target)
        self.playthrough_selector.setCurrentIndex(max(0, selector_index))
        self.playthrough_selector.blockSignals(False)
        official_template = (
            self.template_registry.from_payload(state.official_journey_template)
            or self.template_registry.doom_eternal()
        )
        journey = self.journey_builder.build(
            state,
            official_template,
            playthrough_id=self.selected_playthrough_id,
        )
        self.journey_page.set_presentation(journey)
        # Every selected playthrough is the user's personal history and can be
        # completed with memories, screenshots and ratings later.  Selection,
        # not recency, defines the editing target.
        self.journey_page.set_editable(journey.playthrough_id is not None)
        self.creator_source_model = self.creator_builder.build(journey)
        actions = tuple(action for action in state.actions if action is not GameRowAction.OPEN)
        self._configure_actions(actions)

    def _switch_playthrough(self) -> None:
        value = self.playthrough_selector.currentData()
        if value is not None:
            self.selected_playthrough_id = str(value)
        self.refresh()

    def _select_journey_playthrough(self, playthrough_id: str) -> None:
        """Reuse the stable legacy selector as adapter state without rebuilding UI."""
        index = self.playthrough_selector.findData(playthrough_id)
        if index < 0 or index == self.playthrough_selector.currentIndex():
            return
        self.playthrough_selector.blockSignals(True)
        self.playthrough_selector.setCurrentIndex(index)
        self.playthrough_selector.blockSignals(False)
        self.selected_playthrough_id = playthrough_id
        self.refresh()

    def _create_playthrough(self) -> None:
        if self.slice is None:
            return
        try:
            self.selected_playthrough_id = self.slice.create_playthrough()
            self.feedback.setStyleSheet(f"color:{SUCCESS};")
            self.feedback.setText("Новое прохождение создано")
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _request_delete_playthrough(self, playthrough_id: str) -> None:
        if self.slice is None:
            return
        try:
            state = self.slice.load_detail()
            target = next(
                (item for item in state.playthroughs
                 if item.playthrough_id == playthrough_id),
                None,
            )
            if target is None:
                return
            display_number = next(
                index for index, item in enumerate(state.playthroughs, 1)
                if item.playthrough_id == playthrough_id
            )
            if not self._confirm_delete_playthrough(display_number):
                return
            self.selected_playthrough_id = self.slice.delete_playthrough(
                playthrough_id
            )
            self.feedback.setStyleSheet(f"color:{SUCCESS};")
            self.feedback.setText("Прохождение удалено")
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _confirm_delete_playthrough(self, sequence_no: int) -> bool:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Удаление прохождения")
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(f"Удалить «Прохождение №{sequence_no}»?")
        dialog.setInformativeText(
            "Все связанные с этим прохождением данные будут удалены:\n"
            "• состояния этапов;\n"
            "• оценки;\n"
            "• mood;\n"
            "• впечатления;\n"
            "• события;\n"
            "• пользовательские теги;\n"
            "• время и прогресс.\n\n"
            "Это действие нельзя отменить."
        )
        cancel = dialog.addButton("ОТМЕНА", QMessageBox.ButtonRole.RejectRole)
        delete = dialog.addButton(
            "УДАЛИТЬ", QMessageBox.ButtonRole.DestructiveRole
        )
        delete.setStyleSheet(
            "QPushButton{background:#7A2026;border:1px solid #E04B4B;"
            "color:white;font-weight:700;padding:7px 16px;border-radius:6px;}"
            "QPushButton:hover{background:#A52B32;border-color:#FF7770;}"
        )
        dialog.setDefaultButton(cancel)
        dialog.exec()
        return dialog.clickedButton() is delete

    def _refresh_creator_sources(self) -> None:
        if self.slice is None:
            return
        try:
            state = self.slice.load_detail()
            official_template = (
                self.template_registry.from_payload(
                    state.official_journey_template
                )
                or self.template_registry.doom_eternal()
            )
            journey = self.journey_builder.build(
                state, official_template,
                playthrough_id=self.selected_playthrough_id,
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
            # AW0.23 exposes these tasks as contextual cards inside Journey.
            button.setVisible(False)
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
        mood_id: str | None,
    ) -> None:
        """Persist the compact editor through the existing AW0.2 services."""
        if self.slice is None:
            return
        try:
            stage_number = max(1, int(stage_id.rsplit("-", 1)[-1]))
            stages = (
                self.journey_page._model.stages
                if self.journey_page._model is not None else ()
            )
            stage_title = (
                stages[min(stage_number - 1, len(stages) - 1)].title
                if stages else f"Этап {stage_number}"
            )
            # A chapter state must never rewrite the lifecycle state of the
            # whole playthrough.  Earlier code could accidentally create a new
            # run while a player was only adding a memory to a completed one.
            # The chapter progression is represented by its stage-bound
            # checkpoint/rating/impression records.
            checkpoint = (
                CheckpointType.START
                if stage_number == 1
                else CheckpointType.END
                if stage_number == len(stages)
                else CheckpointType.MIDDLE
            )
            if rating is not None or status == "completed":
                self.slice.save_checkpoint(
                    checkpoint,
                    title=stage_title,
                    rating=rating,
                    playthrough_id=self.selected_playthrough_id,
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
                    playthrough_id=self.selected_playthrough_id,
                )
            self.slice.set_stage_mood(
                stage_id, mood_id,
                playthrough_id=self.selected_playthrough_id,
            )
            self.feedback.setStyleSheet(f"color:{SUCCESS};")
            self.feedback.setText("Этап сохранён")
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _set_stage_state(self, stage_id: str, state: str) -> None:
        if self.slice is None:
            return
        try:
            self.slice.set_stage_state(
                stage_id, state,
                playthrough_id=self.selected_playthrough_id,
            )
            model = self.journey_page._model
            if (
                state == "completed" and model is not None and model.stages
                and stage_id == model.stages[-1].stage_id
                and QMessageBox.question(
                    self, "Завершить прохождение",
                    "Последний этап завершён. Завершить всё прохождение?",
                    QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes,
                    QMessageBox.StandardButton.No,
                ) == QMessageBox.StandardButton.Yes
            ):
                self.slice.set_status("ПРОШЁЛ")
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _set_stage_rating(self, stage_id: str, rating: float) -> None:
        if self.slice is None:
            return
        try:
            self.slice.set_stage_rating(
                stage_id, rating, playthrough_id=self.selected_playthrough_id,
            )
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _set_stage_favorite(self, stage_id: str, favorite: bool) -> None:
        if self.slice is None:
            return
        try:
            self.slice.set_stage_favorite(
                stage_id, favorite,
                playthrough_id=self.selected_playthrough_id,
            )
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _set_stage_media(self, stage_id: str, path: str) -> None:
        if self.slice is None:
            return
        try:
            self.slice.set_stage_media(
                stage_id, path, playthrough_id=self.selected_playthrough_id,
            )
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _save_journey_entry(self, draft) -> None:
        """Persist a typed, explicitly stage-bound Journey event."""
        if self.slice is None:
            return
        try:
            file_path = str(draft.metadata.get("file_path", "")).strip()
            if file_path:
                self.slice.set_stage_media(
                    draft.stage_id, file_path,
                    playthrough_id=self.selected_playthrough_id,
                )
            event_type = {
                "favorite": "favorite_moment", "challenge": "difficult_moment",
                "rating": "rating_change",
            }.get(draft.event_type, draft.event_type)
            self.slice.add_timeline_event(
                draft.stage_id, event_type, title=draft.title, body=draft.body,
                tags=draft.tags, media_path=file_path or None,
                rating_after=draft.rating, occurred_at=draft.occurred_at or None,
                mood_id=draft.mood_id,
                playthrough_id=self.selected_playthrough_id,
            )
            if draft.mood_id:
                self.slice.set_stage_mood(
                    draft.stage_id, draft.mood_id,
                    playthrough_id=self.selected_playthrough_id,
                )
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _revise_journey_entry(self, value) -> None:
        if self.slice is None:
            return
        event_id, draft = value
        try:
            self.slice.revise_timeline_event(
                event_id, title=draft.title, body=draft.body, tags=draft.tags,
                rating_after=draft.rating, mood_id=draft.mood_id,
                occurred_at=draft.occurred_at or None,
                playthrough_id=self.selected_playthrough_id,
            )
            self.refresh()
            self.changed.emit()
        except Exception as exc:
            self._error(str(exc))

    def _delete_journey_entry(self, event_id: str) -> None:
        if self.slice is None:
            return
        try:
            self.slice.delete_timeline_event(
                event_id, playthrough_id=self.selected_playthrough_id
            )
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
                    self.slice.add_playtime(
                        *value, playthrough_id=self.selected_playthrough_id
                    )
            elif action is GameRowAction.ADD_CHECKPOINT:
                state = self.slice.load_detail()
                value = request_checkpoint(
                    self, state.row.total_playtime_minutes
                )
                if value:
                    self.slice.save_checkpoint(
                        **value, playthrough_id=self.selected_playthrough_id
                    )
            elif action is GameRowAction.ADD_IMPRESSION:
                value = request_impression(self)
                if value:
                    self.slice.add_impression(
                        *value, playthrough_id=self.selected_playthrough_id
                    )
            elif action is GameRowAction.RATE:
                value = request_personal_rating(self)
                if value:
                    self.slice.save_personal_rating(
                        *value, playthrough_id=self.selected_playthrough_id
                    )
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
