"""Reusable Journey timeline widgets for game detail pages.

This module is intentionally presentation-only.  Persistence is requested
through signals and remains owned by the application/service adapter.
"""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.journey_presentation import (
    JourneyEntry,
    JourneyPresentation,
    JourneyStage,
)
from app.core.constants import ACCENT, SUCCESS, WARNING


STATUS_LABELS = {
    None: "Не начато",
    "planned": "Запланировано",
    "playing": "Прохожу",
    "completed": "Пройдено",
    "abandoned": "Брошено",
}


def _duration(minutes: int) -> str:
    if not minutes:
        return "—"
    hours, remainder = divmod(minutes, 60)
    return f"{hours} ч {remainder:02d} мин" if remainder else f"{hours} ч"


def _date_time(value: str) -> str:
    return value[:16].replace("T", " ") if value else "—"


class EmptyStatePanel(QFrame):
    """Compact finished-looking empty state shared by Journey sections."""

    action_requested = Signal()

    def __init__(
        self, title: str, text: str, action_text: str = "", parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("journeyEmpty")
        self.setStyleSheet(
            "QFrame#journeyEmpty{background:#0B141C;border:0;"
            "border-radius:8px;}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        heading = QLabel(title)
        heading.setStyleSheet("font-size:11pt;font-weight:700;color:#EEF1F4;")
        detail = QLabel(text)
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        copy.addWidget(heading)
        copy.addWidget(detail)
        layout.addLayout(copy, 1)
        if action_text:
            action = QPushButton(action_text)
            action.clicked.connect(self.action_requested.emit)
            layout.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)


class JourneyEntryCard(QFrame):
    """Compact memory entry inside the selected Journey stage."""

    def __init__(self, entry: JourneyEntry, parent=None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("journeyEntry")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self.setStyleSheet(
            "QFrame#journeyEntry{background:#0B141C;border:0;"
            "border-radius:7px;}"
            f"QFrame#journeyEntry:hover{{background:#160B24;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(6)
        top = QHBoxLayout()
        title = QLabel(entry.title)
        title.setWordWrap(True)
        title.setStyleSheet("font-weight:700;color:white;")
        top.addWidget(title, 1)
        when = QLabel(_date_time(entry.occurred_at))
        when.setObjectName("muted")
        top.addWidget(when)
        layout.addLayout(top)
        if entry.body:
            body = QLabel(entry.body)
            body.setWordWrap(True)
            body.setObjectName("muted")
            layout.addWidget(body)
        if entry.rating is not None:
            rating = QLabel(f"{entry.rating:.1f}")
            rating.setStyleSheet(
                f"color:{WARNING};font-size:13pt;font-weight:800;border:0;"
            )
            layout.addWidget(rating, 0, Qt.AlignmentFlag.AlignRight)


class CheckpointCard(JourneyEntryCard):
    pass


class KeyMomentCard(JourneyEntryCard):
    pass


class ImpressionCard(JourneyEntryCard):
    pass


class JourneyTimelineNode(QPushButton):
    """Stable compact node in a horizontal Journey route."""

    stage_selected = Signal(str)

    def __init__(
        self, stage: JourneyStage, state: str, index: int, parent=None,
    ) -> None:
        super().__init__(parent)
        self.stage = stage
        self.index = index
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(142, 76)
        self.setProperty("journeyState", state)
        self.setToolTip(stage.title)
        self.clicked.connect(lambda: self.stage_selected.emit(stage.stage_id))
        self._apply_text()
        self._apply_style()

    def _apply_text(self) -> None:
        rating = next(
            (entry.rating for entry in reversed(self.stage.entries)
             if entry.rating is not None),
            None,
        )
        material = "  •" if self.stage.entries else ""
        footer = f"{rating:.1f}{material}" if rating is not None else (
            f"Есть запись{material}" if self.stage.entries else "Впереди"
        )
        title = self.stage.title
        if len(title) > 22:
            title = title[:20].rstrip() + "…"
        self.setText(f"{self.index:02d}  {title}\n{footer}")

    def set_selected(self, selected: bool) -> None:
        self.setChecked(selected)
        self._apply_style()

    def _apply_style(self) -> None:
        state = self.property("journeyState")
        border = "#3B4650"
        background = "#111820"
        color = "#98A2AC"
        if state == "complete":
            border, background, color = "#197044", "#10251B", "#75E4A6"
        elif state == "active":
            border, background, color = "#A87800", "#2A2108", "#FFD45A"
        elif state == "abandoned":
            border, background, color = "#8D3030", "#2B1113", "#FF8989"
        if self.isChecked():
            border = ACCENT
            color = "#FFFFFF"
        self.setStyleSheet(
            "QPushButton{"
            f"background:{background};border:1px solid {border};"
            f"border-radius:7px;color:{color};padding:8px 10px;"
            "text-align:left;font-weight:600;}"
            f"QPushButton:hover{{background:#160B24;border-color:{ACCENT};"
            "color:white;}"
        )


# Compatibility name retained for code/tests written before the AW0.21 rework.
JourneyStageCard = JourneyTimelineNode


class JourneyQuickEditor(QFrame):
    """Inline four-step editor; the adapter performs the actual writes."""

    save_requested = Signal(str, str, object, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stage_id = ""
        self.setObjectName("journeyQuickEditor")
        self.setStyleSheet(
            "QFrame#journeyQuickEditor{background:#0B141C;"
            "border:0;border-radius:8px;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 11, 13, 12)
        layout.setSpacing(8)
        self.title = QLabel("БЫСТРОЕ ВПЕЧАТЛЕНИЕ")
        self.title.setObjectName("caption")
        layout.addWidget(self.title)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.status = QComboBox()
        for value, label in (
            ("planned", "Запланировано"),
            ("playing", "Прохожу"),
            ("completed", "Завершить этап"),
            ("abandoned", "Брошено"),
        ):
            self.status.addItem(label, value)
        self.rating = QDoubleSpinBox()
        self.rating.setRange(0.0, 10.0)
        self.rating.setSingleStep(0.1)
        self.rating.setDecimals(1)
        self.rating.setSpecialValueText("Без оценки")
        self.rating.setButtonSymbols(
            QDoubleSpinBox.ButtonSymbols.NoButtons
        )
        self.rating.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rating_controls = QHBoxLayout()
        rating_controls.setSpacing(4)
        rating_down = QPushButton("−")
        rating_up = QPushButton("+")
        for button in (rating_down, rating_up):
            button.setFixedSize(32, 34)
        rating_down.clicked.connect(self.rating.stepDown)
        rating_up.clicked.connect(self.rating.stepUp)
        rating_controls.addWidget(rating_down)
        rating_controls.addWidget(self.rating, 1)
        rating_controls.addWidget(rating_up)
        self.impression = QLineEdit()
        self.impression.setPlaceholderText("Короткое впечатление…")
        self.impression.returnPressed.connect(self._emit_save)
        self.save = QPushButton("СОХРАНИТЬ")
        self.save.setProperty("primary", True)
        self.save.clicked.connect(self._emit_save)
        controls.addWidget(self.status, 2)
        controls.addLayout(rating_controls, 2)
        controls.addWidget(self.impression, 5)
        controls.addWidget(self.save)
        layout.addLayout(controls)

    def set_stage(self, stage: JourneyStage, status: str | None) -> None:
        self._stage_id = stage.stage_id
        index = self.status.findData(status or "planned")
        self.status.setCurrentIndex(max(0, index))
        rating = next(
            (entry.rating for entry in reversed(stage.entries)
             if entry.rating is not None),
            0.0,
        )
        self.rating.setValue(rating)
        self.impression.clear()

    def set_editable(self, editable: bool) -> None:
        for widget in (
            self.status, self.rating, self.impression, self.save
        ):
            widget.setEnabled(editable)
        self.title.setText(
            "БЫСТРОЕ ВПЕЧАТЛЕНИЕ"
            if editable
            else "АРХИВ ПРОХОЖДЕНИЯ · ТОЛЬКО ЧТЕНИЕ"
        )

    def _emit_save(self) -> None:
        self.save_requested.emit(
            self._stage_id,
            str(self.status.currentData()),
            self.rating.value() or None,
            self.impression.text().strip(),
        )


class JourneyView(QWidget):
    """One horizontal Journey route and one selected-stage detail card."""

    quick_save_requested = Signal(str, str, object, str)
    stage_selection_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model: JourneyPresentation | None = None
        self._selected_stage_id: str | None = None
        self._stage_buttons: dict[str, JourneyTimelineNode] = {}

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        heading_row = QHBoxLayout()
        heading = QLabel("JOURNEY")
        heading.setStyleSheet("font-size:14pt;font-weight:800;color:#EEF1F4;")
        heading_row.addWidget(heading)
        self.progress = QLabel()
        self.progress.setObjectName("muted")
        heading_row.addWidget(self.progress)
        heading_row.addStretch()
        self.previous = QPushButton("‹")
        self.next = QPushButton("›")
        for button in (self.previous, self.next):
            button.setFixedSize(32, 30)
        self.previous.clicked.connect(lambda: self._move_selection(-1))
        self.next.clicked.connect(lambda: self._move_selection(1))
        heading_row.addWidget(self.previous)
        heading_row.addWidget(self.next)
        self.layout.addLayout(heading_row)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.timeline_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.timeline_scroll.setFixedHeight(104)
        self.timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.timeline_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:0;}"
            "QScrollArea > QWidget > QWidget{background:transparent;}"
        )
        self.timeline_host = QWidget()
        self.timeline_host.setStyleSheet("background:transparent;")
        self.route = QHBoxLayout(self.timeline_host)
        self.route.setContentsMargins(2, 5, 2, 5)
        self.route.setSpacing(0)
        self.timeline_scroll.setWidget(self.timeline_host)
        self.layout.addWidget(self.timeline_scroll)

        self.detail = QFrame()
        self.detail.setObjectName("journeyStageDetail")
        self.detail.setStyleSheet(
            "QFrame#journeyStageDetail{background:#080F15;"
            "border:0;border-radius:9px;}"
        )
        self.detail_layout = QVBoxLayout(self.detail)
        self.detail_layout.setContentsMargins(16, 13, 16, 15)
        self.detail_layout.setSpacing(10)
        detail_heading = QHBoxLayout()
        self.detail_title = QLabel()
        self.detail_title.setStyleSheet(
            "font-size:14pt;font-weight:750;color:white;"
        )
        detail_heading.addWidget(self.detail_title)
        detail_heading.addStretch()
        self.material_count = QLabel()
        self.material_count.setObjectName("muted")
        detail_heading.addWidget(self.material_count)
        self.detail_layout.addLayout(detail_heading)
        self.entries_host = QWidget()
        self.entries_host.setStyleSheet("background:transparent;")
        self.entries_layout = QHBoxLayout(self.entries_host)
        self.entries_layout.setContentsMargins(0, 0, 0, 0)
        self.entries_layout.setSpacing(8)
        self.detail_layout.addWidget(self.entries_host)
        self.quick_editor = JourneyQuickEditor()
        self.quick_editor.save_requested.connect(
            self.quick_save_requested.emit
        )
        self.detail_layout.addWidget(self.quick_editor)
        self.layout.addWidget(self.detail)

    def set_presentation(self, model: JourneyPresentation) -> None:
        old_selection = self._selected_stage_id
        self._model = model
        if old_selection and any(
            stage.stage_id == old_selection for stage in model.stages
        ):
            self._selected_stage_id = old_selection
        else:
            active = self._active_stage_id(model.stages, model.status)
            self._selected_stage_id = active
        self._render_route(model)
        self._render_selected_stage()
        self._ensure_selected_visible()

    def set_editable(self, editable: bool) -> None:
        self.quick_editor.set_editable(editable)

    def _render_route(self, model: JourneyPresentation) -> None:
        self._clear_layout(self.route)
        self._stage_buttons.clear()
        active_id = self._active_stage_id(model.stages, model.status)
        completed = self._completed_stage_ids(model.stages, model.status)
        self.progress.setText(
            f"{len(completed)} из {len(model.stages)} этапов · "
            f"{STATUS_LABELS.get(model.status, 'Не начато')}"
        )
        for index, stage in enumerate(model.stages, start=1):
            state = (
                "abandoned"
                if model.status == "abandoned" and stage.stage_id == active_id
                else "active"
                if model.status == "playing" and stage.stage_id == active_id
                else "complete"
                if stage.stage_id in completed
                else "future"
            )
            button = JourneyTimelineNode(stage, state, index)
            button.stage_selected.connect(self._select_stage)
            button.set_selected(stage.stage_id == self._selected_stage_id)
            self._stage_buttons[stage.stage_id] = button
            self.route.addWidget(button)
            if index < len(model.stages):
                connector = QFrame()
                connector.setFixedSize(22, 2)
                connector.setStyleSheet(
                    f"background:{ACCENT if stage.stage_id in completed else '#26343E'};"
                    "border:0;"
                )
                self.route.addWidget(
                    connector, 0, Qt.AlignmentFlag.AlignVCenter
                )
        self.route.addStretch()

    @staticmethod
    def _completed_stage_ids(
        stages: Iterable[JourneyStage], status: str | None
    ) -> set[str]:
        stages = tuple(stages)
        if status == "completed":
            return {stage.stage_id for stage in stages}
        populated = [index for index, stage in enumerate(stages) if stage.entries]
        if not populated:
            return set()
        last = max(populated)
        return {stage.stage_id for stage in stages[:last]}

    @staticmethod
    def _active_stage_id(
        stages: Iterable[JourneyStage], status: str | None
    ) -> str:
        stages = tuple(stages)
        if not stages:
            return ""
        if status == "completed":
            return stages[-1].stage_id
        populated = [index for index, stage in enumerate(stages) if stage.entries]
        if not populated:
            return stages[0].stage_id
        if status == "abandoned":
            return stages[max(populated)].stage_id
        return stages[min(max(populated) + 1, len(stages) - 1)].stage_id

    def _select_stage(self, stage_id: str) -> None:
        self._selected_stage_id = stage_id
        for key, button in self._stage_buttons.items():
            button.set_selected(key == stage_id)
        self._render_selected_stage()
        self._ensure_selected_visible()
        self.stage_selection_changed.emit(stage_id)

    def _move_selection(self, offset: int) -> None:
        if self._model is None or not self._model.stages:
            return
        ids = [stage.stage_id for stage in self._model.stages]
        try:
            current = ids.index(self._selected_stage_id or ids[0])
        except ValueError:
            current = 0
        self._select_stage(ids[max(0, min(len(ids) - 1, current + offset))])

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._move_selection(-1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self._move_selection(1)
            event.accept()
            return
        super().keyPressEvent(event)

    def _ensure_selected_visible(self) -> None:
        button = self._stage_buttons.get(self._selected_stage_id or "")
        if button is not None:
            self.timeline_scroll.ensureWidgetVisible(button, 24, 0)

    def _render_selected_stage(self) -> None:
        if self._model is None:
            return
        self._clear_layout(self.entries_layout)
        stage = next(
            item for item in self._model.stages
            if item.stage_id == self._selected_stage_id
        )
        index = self._model.stages.index(stage) + 1
        self.detail_title.setText(f"{index:02d} · {stage.title}")
        self.material_count.setText(
            f"{len(stage.entries)} "
            f"{'запись' if len(stage.entries) == 1 else 'записей'}"
        )

        if stage.entries:
            for entry in stage.entries[-3:]:
                card_class = (
                    ImpressionCard
                    if entry.kind == "impression"
                    else KeyMomentCard
                    if entry in self._model.key_moments
                    else CheckpointCard
                )
                self.entries_layout.addWidget(card_class(entry), 1)
        else:
            self.entries_layout.addWidget(
                EmptyStatePanel(
                    "Этап ещё не заполнен",
                    "Зафиксируйте первое впечатление, когда будете готовы.",
                ),
                1,
            )

        self.quick_editor.set_stage(stage, self._model.status)

    @classmethod
    def _clear_layout(cls, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                cls._clear_layout(item.layout())
