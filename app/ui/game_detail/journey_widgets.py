"""Reusable AW0.23 Journey diary widgets for game detail pages.

The module remains presentation-only. Persistence is requested through
signals and is owned by the existing application/service adapter.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
import logging

from PySide6.QtCore import (
    QPoint, QDateTime, QEasingCurve, Property, QPropertyAnimation, QTimer, Qt,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QCursor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
    QMessageBox, QScrollArea, QSizePolicy, QStackedWidget, QTextEdit,
    QTimeEdit, QVBoxLayout, QWidget,
)

from app.application.journey_presentation import (
    JourneyEntry, JourneyPresentation, JourneyStage,
)
from app.application.journey_layout import JourneyTimelineLayoutModel
from app.core.constants import SUCCESS, WARNING
from app.ui.velora_ui.charts import MoodChart, MoodChartPoint
from app.ui.velora_ui.components import (
    VeloraActionCard, VeloraEventCard, VeloraMoodSelector, VeloraRatingSelector,
    VeloraScrollArrow, VeloraStageCard,
)
from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.moods import MoodRegistry
from app.ui.velora_ui.theme.tokens import Colors, Dimensions, Spacing, Typography
from app.ui.rating_palette import rating_color


STATUS_LABELS = {
    None: "Не начато", "planned": "Не начато", "playing": "Текущая",
    "completed": "Завершено", "abandoned": "Брошено",
}
STATUS_LABELS.update({
    "current": "Текущий", "in_progress": "В процессе",
    "not_started": "Не начато", "skipped": "Пропущено",
})
RUN_STATUS_LABELS = {
    None: "Не начато",
    "planned": "Не начато",
    "playing": "Прохожу",
    "completed": "Завершено",
    "abandoned": "Брошено",
}
LOGGER = logging.getLogger(__name__)
EVENT_META = (
    ("note", "journey.note", "Заметка"),
    ("screenshot", "journey.screenshot", "Скриншот"),
    ("achievement", "journey.achievement", "Достижение"),
    ("favorite", "journey.favorite", "Любимый момент"),
    ("music", "journey.music", "Музыка"),
    ("challenge", "journey.difficult", "Сложный момент"),
    ("impression", "journey.impression", "Впечатление"),
    ("other", "journey.other", "Другое"),
)
QUICK_STAGE_IMPRESSIONS = (
    "Сложная миссия",
    "Динамичный бой",
    "Атмосферный этап",
    "Сильный сюжет",
    "Красивый визуал",
    "Запоминающийся момент",
)
def _duration(minutes: int) -> str:
    if not minutes:
        return "Нет данных"
    hours, remainder = divmod(minutes, 60)
    if not hours:
        return f"{remainder} мин"
    return f"{hours} ч {remainder} мин" if remainder else f"{hours} ч"


def _date(value: str | None) -> str:
    if not value:
        return "Нет данных"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    months = (
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    )
    return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}"


def _latest_rating(stage: JourneyStage) -> float | None:
    # An explicit mission rating is the user's final choice for that mission.
    # Event ratings form the fallback average only until that value is set.
    if stage.rating is not None:
        return stage.rating
    event_ratings = tuple(
        entry.rating for entry in stage.entries
        if entry.kind != "rating" and entry.rating is not None
    )
    if event_ratings:
        return sum(event_ratings) / len(event_ratings)
    return next(
        (entry.rating for entry in reversed(stage.entries)
         if entry.rating is not None),
        None,
    )


def _rating_verdict(score: float) -> str:
    """Return the compact qualitative label used beside a Journey score."""
    if score >= 9.0:
        return "Отлично"
    if score >= 7.0:
        return "Хорошо"
    if score >= 5.0:
        return "Средне"
    if score >= 3.0:
        return "Удовлетворительно"
    return "Плохо"


@dataclass(frozen=True, slots=True)
class JourneyEntryDraft:
    stage_id: str
    event_type: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    mood_id: str | None = None
    rating: float | None = None
    occurred_at: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


class JourneyEntryDialog(QDialog):
    """One reusable, type-aware editor for personal Journey memories."""

    TITLES = {
        "note": "НОВАЯ ЗАМЕТКА", "screenshot": "НОВЫЙ СКРИНШОТ",
        "achievement": "НОВОЕ ДОСТИЖЕНИЕ", "favorite": "ЛЮБИМЫЙ МОМЕНТ",
        "challenge": "СЛОЖНЫЙ МОМЕНТ", "music": "МУЗЫКА",
        "impression": "НОВОЕ ВПЕЧАТЛЕНИЕ", "other": "НОВОЕ СОБЫТИЕ",
    }

    def __init__(
        self, stage: JourneyStage, event_type: str, stage_number: int,
        parent=None, entry: JourneyEntry | None = None,
    ) -> None:
        super().__init__(parent)
        self.stage = stage
        self.event_type = event_type
        self.setObjectName("journeyEntryDialog")
        self.setWindowTitle(self.TITLES.get(event_type, "НОВОЕ СОБЫТИЕ"))
        self.setModal(True)
        self.setMinimumSize(820, 660)
        self.setStyleSheet(
            f"QDialog#journeyEntryDialog{{background:{Colors.BACKGROUND_ELEVATED};"
            f"color:{Colors.TEXT_PRIMARY};}}"
            f"QDialog#journeyEntryDialog QLabel#dialogTitle{{color:{Colors.TEXT_PRIMARY};"
            "font-size:24px;font-weight:800;border:0;background:transparent;}"
            f"QDialog#journeyEntryDialog QLabel#dialogContext{{color:{Colors.TEXT_MUTED};"
            "font-size:13px;border:0;background:transparent;}"
            f"QDialog#journeyEntryDialog QLabel#sectionCaption{{color:{Colors.TEXT_SECONDARY};"
            "font-size:11px;font-weight:700;border:0;background:transparent;}"
            "QDialog#journeyEntryDialog QLineEdit,QDialog#journeyEntryDialog QTextEdit,"
            "QDialog#journeyEntryDialog QDateEdit,QDialog#journeyEntryDialog QTimeEdit{"
            f"background:{Colors.SURFACE_INPUT};color:{Colors.TEXT_PRIMARY};"
            f"border:1px solid {Colors.BORDER_DEFAULT};border-radius:7px;"
            "padding:8px 12px;selection-background-color:#6F24A8;}"
            "QDialog#journeyEntryDialog QLineEdit:hover,QDialog#journeyEntryDialog QTextEdit:hover,"
            "QDialog#journeyEntryDialog QDateEdit:hover,QDialog#journeyEntryDialog QTimeEdit:hover{"
            f"border-color:{Colors.BORDER_HOVER};}}"
            "QDialog#journeyEntryDialog QLineEdit:focus,QDialog#journeyEntryDialog QTextEdit:focus,"
            "QDialog#journeyEntryDialog QDateEdit:focus,QDialog#journeyEntryDialog QTimeEdit:focus{"
            f"border-color:{Colors.BORDER_ACTIVE};background:{Colors.BACKGROUND_SECONDARY};}}"
            "QDialog#journeyEntryDialog QDateEdit{padding-right:30px;}"
            "QDialog#journeyEntryDialog QDateEdit::drop-down{background:transparent;"
            "border:0;width:28px;subcontrol-origin:padding;"
            "subcontrol-position:center right;}"
            "QDialog#journeyEntryDialog QDateEdit::down-arrow{width:9px;height:6px;}"
            "QDialog#journeyEntryDialog QPushButton#saveEntryButton{"
            f"background:{Colors.ACCENT_PRESSED};color:{Colors.TEXT_ON_ACCENT};"
            f"border:1px solid {Colors.BORDER_ACTIVE};border-radius:7px;"
            "padding:9px 22px;font-weight:700;}"
            "QDialog#journeyEntryDialog QPushButton#saveEntryButton:hover{"
            f"background:{Colors.ACCENT_PRIMARY};}}"
            "QDialog#journeyEntryDialog QPushButton#cancelEntryButton{"
            f"background:transparent;color:{Colors.TEXT_SECONDARY};border:1px solid transparent;"
            "border-radius:7px;padding:9px 18px;}"
            "QDialog#journeyEntryDialog QPushButton#cancelEntryButton:hover{"
            f"color:{Colors.TEXT_PRIMARY};background:{Colors.BACKGROUND_HOVER};"
            f"border-color:{Colors.BORDER_DEFAULT};}}"
            "QDialog#journeyEntryDialog QDialogButtonBox{background:transparent;border:0;}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(14)
        heading = QLabel(self.TITLES.get(event_type, "НОВОЕ СОБЫТИЕ"))
        heading.setObjectName("dialogTitle")
        root.addWidget(heading)
        stage_label = QLabel(f"{stage_number:02d} · {stage.title}")
        stage_label.setObjectName("dialogContext")
        root.addWidget(stage_label)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(
            f"border:0;border-top:1px solid {Colors.BORDER_SUBTLE};"
        )
        root.addWidget(divider)

        self.title_caption = QLabel("НАЗВАНИЕ")
        self.title_caption.setObjectName("sectionCaption")
        root.addWidget(self.title_caption)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(self._title_placeholder(event_type))
        root.addWidget(self.title_edit)
        self.body_caption = QLabel("ЗАМЕТКА")
        self.body_caption.setObjectName("sectionCaption")
        root.addWidget(self.body_caption)
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText(
            "Какие впечатления остались?" if event_type in ("note", "impression")
            else "Описание события"
        )
        self.body_edit.setFixedHeight(120)
        root.addWidget(self.body_edit)

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Выберите существующий файл")
        if event_type == "screenshot":
            file_row = QHBoxLayout()
            file_row.addWidget(self.file_edit, 1)
            browse = QPushButton("ВЫБРАТЬ ФАЙЛ")
            browse.clicked.connect(self._browse)
            file_row.addWidget(browse)
            root.addLayout(file_row)
            self.file_preview = QLabel("Предпросмотр появится после выбора файла")
            self.file_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_preview.setFixedHeight(90)
            self.file_preview.setStyleSheet(
                "background:#101923;border:1px solid #293744;border-radius:7px;"
                "color:#82909D;"
            )
            root.addWidget(self.file_preview)
        else:
            self.file_edit.hide()
            self.file_preview = None

        self.extra_edit = QLineEdit()
        self.extra_edit.setVisible(event_type in ("achievement", "favorite", "challenge"))
        self.extra_edit.setPlaceholderText({
            "achievement": "Редкость или иконка (необязательно)",
            "favorite": "Категория момента (необязательно)",
            "challenge": "Сложность и количество попыток (необязательно)",
        }.get(event_type, ""))
        root.addWidget(self.extra_edit)

        rating_caption = QLabel("ОЦЕНКА СОБЫТИЯ")
        rating_caption.setObjectName("sectionCaption")
        root.addWidget(rating_caption)
        self.rating_selector = VeloraRatingSelector()
        root.addWidget(self.rating_selector)

        mood_row = QHBoxLayout()
        mood_caption = QLabel("КАК ПРОШЁЛ ЭТАП?")
        mood_caption.setObjectName("sectionCaption")
        mood_row.addWidget(mood_caption)
        self.mood = VeloraMoodSelector()
        self.mood.setMinimumWidth(330)
        mood_row.addWidget(self.mood)
        mood_row.addStretch()
        root.addLayout(mood_row)
        moment_row = QHBoxLayout()
        moment_row.setSpacing(10)
        date_column = QVBoxLayout()
        date_column.setSpacing(4)
        date_caption = QLabel("ДАТА СОБЫТИЯ")
        date_caption.setObjectName("sectionCaption")
        self.event_date = QDateEdit(QDateTime.currentDateTime().date())
        self.event_date.setCalendarPopup(True)
        self.event_date.setDisplayFormat("dd.MM.yyyy")
        self.event_date.setKeyboardTracking(False)
        self.event_date.setFixedWidth(190)
        date_column.addWidget(date_caption)
        date_column.addWidget(self.event_date)
        moment_row.addLayout(date_column)

        time_column = QVBoxLayout()
        time_column.setSpacing(4)
        time_caption = QLabel("ВРЕМЯ")
        time_caption.setObjectName("sectionCaption")
        self.event_time = QTimeEdit(QDateTime.currentDateTime().time())
        self.event_time.setDisplayFormat("HH:mm")
        self.event_time.setAccelerated(True)
        self.event_time.setWrapping(True)
        self.event_time.setKeyboardTracking(False)
        self.event_time.setFixedWidth(140)
        self.event_time.setToolTip(
            "Кликните по часам или минутам и крутите колёсико мыши"
        )
        self.event_time.setStyleSheet(
            "QTimeEdit::up-button,QTimeEdit::down-button{width:0;height:0;border:0;}"
        )
        time_column.addWidget(time_caption)
        time_column.addWidget(self.event_time)
        moment_row.addLayout(time_column)
        moment_row.addStretch()
        root.addLayout(moment_row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("СОХРАНИТЬ")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("ОТМЕНА")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName(
            "saveEntryButton"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setObjectName(
            "cancelEntryButton"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        if entry is not None:
            self.title_edit.setText(entry.title)
            self.body_edit.setPlainText(entry.body)
            self.rating_selector.setValue(entry.rating)
            self.mood.set_mood_id(entry.mood_id)
            stored_time = QDateTime.fromString(
                entry.occurred_at, Qt.DateFormat.ISODate
            )
            if stored_time.isValid():
                self.event_date.setDate(stored_time.date())
                self.event_time.setTime(stored_time.time())

    @staticmethod
    def _title_placeholder(event_type: str) -> str:
        return {
            "note": "Название заметки",
            "impression": "Название впечатления",
            "screenshot": "Подпись к скриншоту",
            "achievement": "Название достижения",
            "favorite": "Название любимого момента",
            "challenge": "Название сложного момента",
            "music": "Название композиции",
            "other": "Название события",
        }.get(event_type, "Название события")

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать скриншот", "", "Изображения (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.file_edit.setText(path)
            if self.file_preview is not None:
                preview = QPixmap(path)
                self.file_preview.setPixmap(preview.scaled(
                    220, 86, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))

    def draft(self) -> JourneyEntryDraft:
        title = self.title_edit.text().strip()
        if not title:
            title = {
                "note": "Заметка", "screenshot": "Скриншот",
                "achievement": "Достижение", "favorite": "Любимый момент",
                "challenge": "Сложный момент", "music": "Музыка",
                "impression": "Личное впечатление", "other": "Другое событие",
            }.get(self.event_type, "Событие")
        return JourneyEntryDraft(
            self.stage.stage_id, self.event_type, title,
            self.body_edit.toPlainText().strip(), (),
            self.mood.mood_id(), self.rating_selector.value(),
            QDateTime(
                self.event_date.date(), self.event_time.time()
            ).toString(Qt.DateFormat.ISODate),
            {
                "file_path": self.file_edit.text(),
                "extra": self.extra_edit.text().strip(),
            },
        )


class JourneyTimelineCanvas(QFrame):
    """Paints one continuous route behind all stage/event columns."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("journeyView")
        self.setStyleSheet("QWidget#journeyView{background:transparent;border:0;}")
        self._count = 0
        self._states: tuple[str, ...] = ()
        self._selected = -1
        self._centers: tuple[int, ...] = ()
        self._line_end: int | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background:transparent;border:0;")

    def set_route(
        self, states: Iterable[str], selected: int,
        centers: Iterable[int] = (),
        line_end: int | None = None,
    ) -> None:
        self._states = tuple(states)
        self._count = len(self._states)
        self._selected = selected
        self._centers = tuple(centers)
        self._line_end = line_end
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._count:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT + 31
        centers = self._centers or tuple(
            Dimensions.JOURNEY_COMPACT_STAGE_WIDTH // 2
            + (Dimensions.JOURNEY_COMPACT_STAGE_WIDTH + 14) * index
            for index in range(self._count)
        )
        first = centers[0]
        last = max(centers[-1], self._line_end or centers[-1])
        painter.setPen(QPen(QColor(Colors.TEXT_MUTED), 2))
        painter.drawLine(first, y, last, y)
        colors = {
            "completed": Colors.STATUS_COMPLETED,
            "current": Colors.STATUS_CURRENT,
            "in_progress": Colors.STATUS_IN_PROGRESS,
            "skipped": Colors.TEXT_MUTED,
            "not_started": Colors.STATUS_NOT_STARTED,
        }
        for index, state in enumerate(self._states):
            x = centers[index]
            color = QColor(colors.get(state, Colors.STATUS_NOT_STARTED))
            painter.setPen(QPen(color, 2))
            painter.drawLine(x, Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT, x, y)
            painter.setBrush(color)
            painter.drawEllipse(x - 5, y - 5, 10, 10)
            if index == self._selected:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(Colors.BORDER_ACTIVE), 2))
                painter.drawEllipse(x - 8, y - 8, 16, 16)


class EmptyStatePanel(QFrame):
    """Finished-looking empty state shared by Journey sections."""

    def __init__(self, title: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("journeyEmpty")
        self.setStyleSheet(
            "QFrame#journeyEmpty{background:#0B141C;border:0;border-radius:8px;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(3)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight:700;color:#EEF1F4;")
        detail = QLabel(text)
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(detail)


class JourneyEntryCard(QFrame):
    """Compact memory entry inside the selected Journey stage."""

    def __init__(self, entry: JourneyEntry, parent=None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("journeyEntry")
        self.setStyleSheet(
            "QFrame#journeyEntry{background:#0C141D;border:1px solid #25323E;"
            "border-radius:7px;}QFrame#journeyEntry:hover{border-color:#8241C9;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(3)
        top = QHBoxLayout()
        title = QLabel(entry.title)
        title.setStyleSheet("font-weight:700;color:white;border:0;")
        top.addWidget(title, 1)
        when = QLabel(_date(entry.occurred_at))
        when.setObjectName("muted")
        top.addWidget(when)
        layout.addLayout(top)
        if entry.body:
            body = QLabel(entry.body)
            body.setWordWrap(True)
            body.setObjectName("muted")
            layout.addWidget(body)


class CheckpointCard(JourneyEntryCard):
    pass


class KeyMomentCard(JourneyEntryCard):
    pass


class ImpressionCard(JourneyEntryCard):
    pass


class JourneyStageArtwork(QLabel):
    """Reusable local-image drop zone for the selected Journey stage."""

    file_selected = Signal(str)
    _extensions = {".png", ".jpg", ".jpeg", ".webp"}
    PREVIEW_WIDTH = 300
    PREVIEW_HEIGHT = 169
    RECOMMENDED_SIZES = "Full HD 1920×1080 или 2K 2560×1440 (16:9)"

    def __init__(self, parent=None) -> None:
        super().__init__("ИЗОБРАЖЕНИЕ ЭТАПА\nПеретащите файл или дважды нажмите")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        # The local source is kept at its original resolution.  Only this
        # 16:9 viewport is scaled, so Full HD and 2K screenshots are neither
        # stretched nor rewritten on disk.
        self.setFixedSize(self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT)
        self.setStyleSheet(
            f"QLabel{{background:{Colors.BACKGROUND_ELEVATED};"
            f"border:1px dashed {Colors.BORDER_DEFAULT};border-radius:8px;"
            f"color:{Colors.TEXT_MUTED};font-weight:700;padding:6px;}}"
            f"QLabel:hover{{border-color:{Colors.BORDER_ACTIVE};"
            f"background:{Colors.ACCENT_SUBTLE};color:{Colors.TEXT_SECONDARY};}}"
        )

    @classmethod
    def _supported(cls, path: str) -> bool:
        from pathlib import Path
        return Path(path).suffix.casefold() in cls._extensions

    def set_path(self, path: str | None) -> None:
        pixmap = QPixmap(path or "")
        if not pixmap.isNull():
            self.setText("")
            self.setPixmap(pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self.setToolTip(f"{path}\n{self.RECOMMENDED_SIZES}")
            return
        self.setPixmap(QPixmap())
        self.setText("ИЗОБРАЖЕНИЕ ЭТАПА\nПеретащите файл или дважды нажмите")
        self.setToolTip(f"PNG, JPG или WEBP · {self.RECOMMENDED_SIZES}")

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if len(urls) == 1 and urls[0].isLocalFile() and self._supported(urls[0].toLocalFile()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:
        path = event.mimeData().urls()[0].toLocalFile()
        if self._supported(path):
            self.file_selected.emit(path)
            event.acceptProposedAction()
            return
        event.ignore()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self, "Выбрать изображение этапа", "",
                "Изображения (*.png *.jpg *.jpeg *.webp)",
            )
            if path:
                self.file_selected.emit(path)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class JourneyTimelineNode(VeloraStageCard):
    """Large stable chapter card in the single horizontal Journey route."""

    stage_state_requested = Signal(str, str)
    stage_favorite_requested = Signal(str, bool)

    def __init__(
        self, stage: JourneyStage, state: str, index: int, parent=None,
    ) -> None:
        rating = _latest_rating(stage)
        super().__init__(
            stage.stage_id, index, stage.title, state,
            rating=rating, has_events=bool(stage.entries),
            event_count=JourneyTimelineLayoutModel.count_events(stage),
            has_favorite=stage.favorite, mood_id=stage.mood_id, parent=parent,
        )
        self.stage, self.index = stage, index
        self.status_toggled.connect(
            lambda stage_id, completed: self.stage_state_requested.emit(
                stage_id, "completed" if completed else "current"
            )
        )
        self.favorite_toggled.connect(self.stage_favorite_requested.emit)

    def _legacy_text_for_compatibility(self) -> str:
        rating = _latest_rating(self.stage)
        return "—" if rating is None else f"{rating:.1f}"


JourneyStageCard = JourneyTimelineNode


class JourneyEventMarker(VeloraEventCard):
    """Small event marker anchored under a chapter card."""

    selected = Signal(object)
    PREVIEW_MAX_CHARS = 24
    HEADING_MAX_CHARS = 22
    _GENERIC_TITLES = {
        "note": {"заметка"},
        "impression": {"личное впечатление", "впечатление"},
        "screenshot": {"скриншот"},
        "achievement": {"достижение"},
        "favorite": {"любимый момент"},
        "favorite_moment": {"любимый момент"},
        "challenge": {"сложный момент"},
        "difficult": {"сложный момент"},
        "difficult_moment": {"сложный момент"},
        "music": {"музыка"},
        "rating_change": {"изменение оценки", "впечатление"},
        "other": {"другое событие", "событие"},
    }

    _COLORS = {
        "note": Colors.ACCENT_PRIMARY,
        "impression": Colors.ACCENT_PRIMARY,
        "screenshot": "#15B8D1",
        "achievement": Colors.WARNING,
        "favorite": Colors.WARNING,
        "favorite_moment": Colors.WARNING,
        "challenge": Colors.STATUS_IN_PROGRESS,
        "difficult": Colors.STATUS_IN_PROGRESS,
        "difficult_moment": Colors.STATUS_IN_PROGRESS,
        "music": "#D35CFF",
        "rating_change": Colors.STATUS_COMPLETED,
        "other": Colors.ACCENT_PRIMARY,
        "legacy": Colors.TEXT_MUTED,
    }
    _ICONS = {
        "note": "journey.note", "impression": "journey.impression",
        "screenshot": "journey.screenshot",
        "achievement": "journey.achievement",
        "favorite": "journey.favorite",
        "favorite_moment": "journey.favorite",
        "challenge": "journey.difficult", "difficult": "journey.difficult",
        "difficult_moment": "journey.difficult", "music": "journey.music",
        "rating_change": "journey.rating_change", "other": "journey.other",
        "legacy": "journey.other",
    }
    _LABELS = {
        "note": "ЗАМЕТКА", "impression": "ВПЕЧАТЛЕНИЕ",
        "screenshot": "СКРИНШОТ", "achievement": "ДОСТИЖЕНИЕ",
        "favorite": "ЛЮБИМЫЙ МОМЕНТ", "favorite_moment": "ЛЮБИМЫЙ МОМЕНТ",
        "challenge": "СЛОЖНЫЙ МОМЕНТ", "difficult": "СЛОЖНЫЙ МОМЕНТ",
        "difficult_moment": "СЛОЖНЫЙ МОМЕНТ", "music": "МУЗЫКА",
        "rating_change": "ОЦЕНКА", "other": "СОБЫТИЕ", "legacy": "СОБЫТИЕ",
    }

    @classmethod
    def icon_key(cls, entry: JourneyEntry) -> str:
        if entry.kind == "impression":
            return "journey.impression"
        if entry.rating is not None:
            return "journey.rating_change"
        return cls._ICONS.get(entry.kind, "journey.other")

    @classmethod
    def color(cls, entry: JourneyEntry) -> str:
        if entry.rating is not None:
            return Colors.STATUS_COMPLETED
        return cls._COLORS.get(entry.kind, Colors.ACCENT_PRIMARY)

    @classmethod
    def preview_text(cls, entry: JourneyEntry) -> str:
        """Return the compact description shown below the event heading."""
        text = " ".join(entry.body.strip().split())
        if len(text) <= cls.PREVIEW_MAX_CHARS:
            return text
        return text[:cls.PREVIEW_MAX_CHARS - 3].rstrip() + "..."

    @classmethod
    def heading_text(cls, entry: JourneyEntry) -> str:
        """Return a stable event heading without consuming its description."""
        text = " ".join(entry.title.strip().split())
        if not text:
            text = cls._LABELS.get(entry.kind, "СОБЫТИЕ").title()
        if len(text) <= cls.HEADING_MAX_CHARS:
            return text
        return text[:cls.HEADING_MAX_CHARS - 3].rstrip() + "..."

    def __init__(self, entry: JourneyEntry, parent=None) -> None:
        icon_key = self.icon_key(entry)
        super().__init__(
            icon_key,
            self.heading_text(entry),
            self.preview_text(entry),
            tooltip=entry.body or entry.title,
            parent=parent,
        )
        self.entry = entry
        self.kind_label.setToolTip(entry.title or self.heading_text(entry))
        self.title_label.setToolTip(entry.body or self.preview_text(entry))
        self.setFixedWidth(JourneyTimelineLayoutModel.EVENT_SLOT_WIDTH)
        self.setFixedHeight(114)
        color = self.color(entry)
        node = QFrame()
        node.setFixedSize(12, 12)
        node.setStyleSheet(
            f"QFrame{{background:{Colors.SURFACE_CARD};border:2px solid {color};"
            "border-radius:6px;}"
        )
        connector = QFrame()
        connector.setFixedSize(2, 12)
        connector.setStyleSheet(
            f"QFrame{{background:{color};border:0;}}"
        )
        self.layout().insertWidget(0, node, 0, Qt.AlignmentFlag.AlignHCenter)
        self.layout().insertWidget(1, connector, 0, Qt.AlignmentFlag.AlignHCenter)
        metadata = QWidget()
        metadata.setStyleSheet("background:transparent;border:0;")
        metadata_row = QHBoxLayout(metadata)
        metadata_row.setContentsMargins(2, 0, 2, 0)
        metadata_row.setSpacing(4)
        metadata_row.addStretch()
        if entry.rating is not None:
            rating_label = QLabel(f"{entry.rating:.1f}")
            rating_label.setStyleSheet(
                f"color:{rating_color(entry.rating)};font-weight:700;border:0;"
            )
            rating_label.setToolTip("Оценка события")
            metadata_row.addWidget(rating_label)
        mood = MoodRegistry.get(entry.mood_id)
        if mood is not None:
            mood_icon = QLabel()
            mood_icon.setPixmap(IconProvider.pixmap(
                mood.icon_key, Dimensions.ICON_SMALL, mood.color
            ))
            mood_icon.setToolTip(mood.display_name)
            metadata_row.addWidget(mood_icon)
        metadata_row.addStretch()
        metadata.setVisible(entry.rating is not None or mood is not None)
        self.layout().addWidget(metadata)
        self.setFixedHeight(158 if metadata.isVisible() else 136)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QFrame#veloraEventCard{background:transparent;border:1px solid transparent;"
            "border-radius:7px;}"
            f"QFrame#veloraEventCard:hover{{background:{Colors.ACCENT_SUBTLE};"
            f"border-color:{color};}}"
        )

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.entry)
        super().mouseReleaseEvent(event)


class JourneyActionCard(VeloraActionCard):
    """Card-like action; never presents itself as a generic button."""

    activated = Signal(str, str)

    def __init__(self, kind: str, icon: str, text: str, parent=None) -> None:
        super().__init__(kind, icon, text, parent)
        self.kind = kind
        self.setMinimumSize(128, 90)
        self.setMaximumSize(16777215, 90)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.icon_label.setPixmap(IconProvider.pixmap(
            icon, 28, Colors.ACCENT_PRIMARY
        ))
        self.text_label.setMaximumHeight(38)
        self.text_label.setStyleSheet(
            f"color:{Colors.TEXT_PRIMARY};border:0;font-size:10pt;font-weight:600;"
        )


class JourneyQuickEditor(QFrame):
    """Inline diary editor; existing adapter still performs actual writes."""

    save_requested = Signal(str, str, object, str, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stage_id = ""
        self.setObjectName("journeyQuickEditor")
        self.setStyleSheet(
            "QFrame#journeyQuickEditor{background:transparent;border:0;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.title = QLabel("КАКИЕ ВПЕЧАТЛЕНИЯ ОСТАЛИСЬ?")
        self.title.setObjectName("caption")
        layout.addWidget(self.title)
        self.impression = QTextEdit()
        self.impression.setPlaceholderText(
            "Что запомнилось? Что удивило или понравилось больше всего?"
        )
        self.impression.setMinimumHeight(96)
        self.impression.setMaximumHeight(116)
        layout.addWidget(self.impression)
        mood_row = QHBoxLayout()
        mood_row.setSpacing(Spacing.SPACE_8)
        mood_label = QLabel("КАК ПРОШЁЛ ЭТАП?")
        mood_label.setObjectName("caption")
        self.mood = VeloraMoodSelector()
        self.mood.setMinimumWidth(180)
        mood_row.addWidget(mood_label)
        mood_row.addWidget(self.mood)
        mood_row.addStretch()
        layout.addLayout(mood_row)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        self.status = QComboBox()
        for value, label in (
            ("planned", "Не начато"), ("playing", "Текущая"),
            ("completed", "Завершено"), ("abandoned", "Брошено"),
        ):
            self.status.addItem(label, value)
        self.status.setMinimumWidth(125)
        controls.addWidget(self.status)
        controls.addStretch()
        self.save = QPushButton("СОХРАНИТЬ ЗАПИСЬ")
        self.save.setProperty("primary", True)
        self.save.clicked.connect(self._emit_save)
        controls.addWidget(self.save)
        layout.addLayout(controls)
        rating_row = QHBoxLayout()
        rating_row.setSpacing(Spacing.SPACE_6)
        rating_row.addWidget(QLabel("ОЦЕНКА ЭТАПА"))
        self.rating = VeloraRatingSelector()
        rating_row.addWidget(self.rating)
        rating_row.addStretch()
        layout.addLayout(rating_row)

    def set_stage(self, stage: JourneyStage, status: str | None, minutes: int = 0) -> None:
        self._stage_id = stage.stage_id
        index = self.status.findData(status or "planned")
        self.status.setCurrentIndex(max(0, index))
        self.rating.setValue(_latest_rating(stage))
        self.mood.set_mood_id(stage.mood_id)
        self.impression.clear()

    def prepare_event(self, label: str) -> None:
        prefix = f"{label}: "
        if not self.impression.toPlainText().strip():
            self.impression.setPlainText(prefix)
        self.impression.setFocus()
        cursor = self.impression.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.impression.setTextCursor(cursor)

    def set_editable(self, editable: bool) -> None:
        for widget in (
            self.status, self.rating, self.impression, self.save, self.mood,
        ):
            widget.setEnabled(editable)
        self.title.setText(
            "КАКИЕ ВПЕЧАТЛЕНИЯ ОСТАЛИСЬ?"
            if editable else "АРХИВ ПРОХОЖДЕНИЯ · ТОЛЬКО ЧТЕНИЕ"
        )

    def _emit_save(self) -> None:
        text = self.impression.toPlainText().strip()
        self.save_requested.emit(
            self._stage_id, str(self.status.currentData()),
            self.rating.value(), text, self.mood.mood_id(),
        )


class JourneyMoodGraph(MoodChart):
    """Lightweight, data-driven line graph for chapter ratings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values: tuple[float | None, ...] = ()
        self.setToolTip("Оценки и настроение по этапам Journey")

    def set_values(self, values: Iterable[float | None]) -> None:
        self._values = tuple(values)
        self.set_points(
            MoodChartPoint(index, rating=value)
            for index, value in enumerate(self._values, 1)
        )


class JourneyView(QWidget):
    """Approved AW0.23 Journey composition over the existing read model."""

    quick_save_requested = Signal(str, str, object, str, object)
    stage_selection_changed = Signal(str)
    new_playthrough_requested = Signal()
    playthrough_selection_requested = Signal(str)
    playthrough_delete_requested = Signal(str)
    entry_requested = Signal(object)
    stage_state_requested = Signal(str, str)
    stage_rating_requested = Signal(str, float)
    stage_favorite_requested = Signal(str, bool)
    stage_media_requested = Signal(str, str)
    event_revision_requested = Signal(object)
    event_delete_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model: JourneyPresentation | None = None
        self._selected_stage_id: str | None = None
        self._selected_event_id: str | None = None
        self._stage_buttons: dict[str, JourneyTimelineNode] = {}
        self._editable = True
        self._scroll_animation: QPropertyAnimation | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.page_scroll = None

        journey_row = QHBoxLayout()
        journey_row.setSpacing(Spacing.SPACE_12)
        self.run_card = self._build_run_card()
        journey_row.addWidget(self.run_card, 0)
        route_panel = QFrame()
        route_panel.setObjectName("journeyRoutePanel")
        route_panel.setMinimumHeight(Dimensions.JOURNEY_ROUTE_MIN_HEIGHT)
        route_panel.setMaximumHeight(Dimensions.JOURNEY_ROUTE_MAX_HEIGHT)
        route_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        route_panel.setStyleSheet(
            "QFrame#journeyRoutePanel{background:#0A1119;border:1px solid #23303B;"
            "border-radius:9px;}"
        )
        route_layout = QVBoxLayout(route_panel)
        route_layout.setContentsMargins(14, 11, 14, 10)
        route_layout.setSpacing(Spacing.SPACE_8)
        route_header = QHBoxLayout()
        title = QLabel("ВАШ ПУТЬ")
        title.setStyleSheet("font-size:12pt;font-weight:800;color:white;")
        route_header.addWidget(title)
        self.progress = QLabel()
        self.progress.setObjectName("muted")
        route_header.addStretch()
        route_header.addWidget(self.progress)
        route_layout.addLayout(route_header)
        legend = QHBoxLayout()
        legend.setSpacing(Spacing.SPACE_12)
        for icon_key, label, color in (
            ("status.completed", "Завершено", Colors.STATUS_COMPLETED),
            ("status.current", "Текущая", Colors.STATUS_CURRENT),
            ("status.in_progress", "В процессе", Colors.STATUS_IN_PROGRESS),
            ("status.not_started", "Не начато", Colors.STATUS_NOT_STARTED),
            ("journey.favorite", "Любимый момент", Colors.TEXT_SECONDARY),
            ("journey.note", "Заметка", Colors.TEXT_SECONDARY),
            ("journey.achievement", "Достижение", Colors.TEXT_SECONDARY),
        ):
            icon = QLabel()
            icon.setPixmap(IconProvider.pixmap(icon_key, 14, color))
            text = QLabel(label)
            text.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};border:0;")
            legend.addWidget(icon)
            legend.addWidget(text)
        legend.addStretch()
        route_layout.addLayout(legend)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        # Route navigation is owned by the two Velora arrow controls.  Keep the
        # native bar hidden: it steals vertical space from event captions and
        # creates a second, competing navigation affordance.
        self.timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_scroll.setMinimumHeight(
            Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT
            + Dimensions.JOURNEY_EVENT_AREA_HEIGHT
            + 20
        )
        self.timeline_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.timeline_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:0;}"
            "QScrollArea QWidget#qt_scrollarea_viewport{background:transparent;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
        )
        self.timeline_scroll.viewport().setStyleSheet(
            "background:transparent;border:0;"
        )
        self.timeline_host = QWidget()
        self.timeline_host.setStyleSheet("background:transparent;")
        self.timeline_canvas = JourneyTimelineCanvas(self.timeline_host)
        self.timeline_canvas.lower()
        self.route = QHBoxLayout(self.timeline_host)
        # A little breathing room below the event lane keeps captions clear of
        # the panel edge without changing the stage-card geometry.
        self.route.setContentsMargins(2, 7, 2, 9)
        self.route.setSpacing(14)
        self.route.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.timeline_scroll.setWidget(self.timeline_host)
        timeline_navigation = QHBoxLayout()
        timeline_navigation.setContentsMargins(0, 0, 0, 0)
        timeline_navigation.setSpacing(7)
        self.route_previous = VeloraScrollArrow("left")
        self.route_next = VeloraScrollArrow("right")
        for button in (self.route_previous, self.route_next):
            button.setFixedSize(
                Dimensions.JOURNEY_SCROLL_ARROW_WIDTH,
                Dimensions.JOURNEY_SCROLL_ARROW_HEIGHT,
            )
        self.route_previous.step_requested.connect(lambda: self._move_route(-1))
        self.route_next.step_requested.connect(lambda: self._move_route(1))
        self.route_previous_host = self._build_route_arrow_host(
            self.route_previous
        )
        self.route_next_host = self._build_route_arrow_host(self.route_next)
        route_bar = self.timeline_scroll.horizontalScrollBar()
        route_bar.rangeChanged.connect(self._update_route_arrows)
        route_bar.valueChanged.connect(lambda _: self._update_route_arrows())
        timeline_navigation.addWidget(self.route_previous_host, 0)
        timeline_navigation.addWidget(self.timeline_scroll, 1)
        timeline_navigation.addWidget(self.route_next_host, 0)
        route_layout.addLayout(timeline_navigation)
        journey_row.addWidget(route_panel, 1)
        # Keep the three Journey zones adjacent. Stretch factors combined with
        # per-zone maximum heights make QVBoxLayout reserve oversized cells,
        # which surfaces as large dark gaps between otherwise compact panels.
        root.addLayout(journey_row)

        self.detail = self._build_detail()
        root.addWidget(self.detail)
        self.analytics = self._build_analytics()
        root.addWidget(self.analytics)
        self.setMinimumHeight(
            Dimensions.JOURNEY_ROUTE_MIN_HEIGHT
            + Dimensions.JOURNEY_DETAIL_MIN_HEIGHT
            + Dimensions.JOURNEY_ANALYTICS_MIN_HEIGHT
            + 10 * 2
        )

    @staticmethod
    def _build_route_arrow_host(button: VeloraScrollArrow) -> QWidget:
        """Keep route arrows centred against stage cards, not the event lane."""
        host = QWidget()
        host.setFixedWidth(Dimensions.JOURNEY_SCROLL_ARROW_WIDTH)
        host.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        host.setStyleSheet("background:transparent;border:0;")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        card_top = 7
        layout.addSpacing(
            card_top
            + max(
                0,
                (
                    Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT
                    - Dimensions.JOURNEY_SCROLL_ARROW_HEIGHT
                )
                // 2,
            )
        )
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        return host

    def _build_run_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("journeyRunCard")
        card.setFixedWidth(Dimensions.JOURNEY_SIDEBAR_WIDTH)
        card.setMinimumHeight(Dimensions.JOURNEY_ROUTE_MIN_HEIGHT)
        card.setMaximumHeight(Dimensions.JOURNEY_ROUTE_MAX_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        card.setStyleSheet(
            "QFrame#journeyRunCard{background:#0D141D;border:1px solid #27343F;"
            "border-radius:9px;}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(0)
        self.run_selector = QComboBox()
        self.run_selector.setFixedHeight(34)
        # Keep the popup compact: ten runs fit without scrolling, while the
        # eleventh and subsequent runs remain reachable through its own
        # vertical scrollbar.
        self.run_selector.setMaxVisibleItems(10)
        self.run_selector.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.run_selector.currentIndexChanged.connect(
            lambda: self.playthrough_selection_requested.emit(
                str(self.run_selector.currentData())
            ) if self.run_selector.currentData() is not None else None
        )
        self.run_selector_group = QFrame()
        self.run_selector_group.setObjectName("journeyRunSelectorGroup")
        self.run_selector_group.setFixedHeight(36)
        self.run_selector_group.setStyleSheet(
            "QFrame#journeyRunSelectorGroup{background:#0B141C;"
            "border:1px solid #34414D;border-radius:7px;}"
            "QFrame#journeyRunSelectorGroup:focus-within{border-color:#9B3CFF;}"
        )
        selector_row = QHBoxLayout(self.run_selector_group)
        selector_row.setContentsMargins(1, 1, 1, 1)
        selector_row.setSpacing(0)
        self.run_selector.setFixedHeight(34)
        self.run_selector.setStyleSheet(
            "QComboBox{background:transparent;border:0;border-radius:6px;"
            "padding:0 7px;color:#E9EDF1;}"
            "QComboBox:hover{background:#121D28;}"
            "QComboBox::drop-down{background:transparent;border:0;width:24px;"
            "subcontrol-origin:padding;subcontrol-position:center right;}"
        )
        selector_row.addWidget(self.run_selector, 1)
        self.run_actions = QPushButton()
        self.run_actions.setObjectName("journeyRunActions")
        self.run_actions.setFixedSize(36, 34)
        self.run_actions.setIcon(IconProvider.icon(
            "common.more", 16, Colors.TEXT_SECONDARY
        ))
        self.run_actions.setToolTip("Действия с прохождением")
        self.run_actions.setStyleSheet(
            "QPushButton#journeyRunActions{background:transparent;"
            "border:0;border-left:1px solid #34414D;border-radius:0;"
            "padding:0;}"
            "QPushButton#journeyRunActions:hover{background:#241437;"
            "border-left-color:#9B3CFF;}"
            "QPushButton#journeyRunActions:pressed{background:#321A4C;}"
            "QPushButton#journeyRunActions::menu-indicator{image:none;}"
        )
        self.run_actions_menu = QMenu(self.run_actions)
        self.run_actions_menu.setObjectName("journeyRunMenu")
        self.run_actions_menu.setStyleSheet(
            "QMenu#journeyRunMenu{background:#0D141D;border:1px solid #34414D;"
            "padding:5px;}"
            "QMenu#journeyRunMenu::item{color:#FF7770;padding:8px 14px;"
            "border-radius:5px;}"
            "QMenu#journeyRunMenu::item:selected{background:#3A171C;"
            "color:#FF9B96;}"
        )
        delete_action = QAction(
            IconProvider.icon("common.delete", 16, Colors.DANGER),
            "Удалить прохождение",
            self.run_actions_menu,
        )
        delete_action.triggered.connect(
            lambda: self.playthrough_delete_requested.emit(
                str(self.run_selector.currentData())
            ) if self.run_selector.currentData() is not None else None
        )
        self.run_actions_menu.addAction(delete_action)
        # setMenu() reserves room for a native menu indicator even when its
        # image is hidden. Open the menu explicitly so the more.svg remains
        # optically centred in its segment.
        self.run_actions.clicked.connect(
            lambda: self.run_actions_menu.popup(
                self.run_actions.mapToGlobal(
                    QPoint(0, self.run_actions.height())
                )
            )
        )
        selector_row.addWidget(self.run_actions)
        layout.addWidget(self.run_selector_group)
        layout.addSpacing(5)
        self.run_kind = QLabel("Текущее")
        self.run_kind.setObjectName("muted")
        self.run_kind.setFixedHeight(15)
        layout.addWidget(self.run_kind)
        self.run_divider = QFrame()
        self.run_divider.setFixedHeight(1)
        self.run_divider.setStyleSheet(
            f"background:{Colors.BORDER_SUBTLE};border:0;"
        )
        layout.addSpacing(5)
        layout.addWidget(self.run_divider)
        layout.addSpacing(5)
        self.run_metrics: dict[str, QLabel] = {}
        for key, caption in (
            ("status", "СТАТУС"), ("progress", "ПРОГРЕСС"),
            ("started", "НАЧАТО"),
            ("last_activity", "ПОСЛЕДНЯЯ ИГРА"),
        ):
            label = QLabel(caption)
            label.setObjectName("caption")
            label.setFixedHeight(12)
            value = QLabel("Нет данных")
            value.setStyleSheet("font-weight:700;color:#E9EDF1;border:0;")
            value.setFixedHeight(16)
            self.run_metrics[key] = value
            layout.addWidget(label)
            layout.addWidget(value)
            if key != "last_activity":
                layout.addSpacing(3)
        self.empty_title = QLabel("ПРОХОЖДЕНИЙ ПОКА НЕТ")
        self.empty_title.setStyleSheet("font-weight:800;color:#E9EDF1;border:0;")
        self.empty_text = QLabel(
            "Начните первое прохождение, чтобы вести Journey."
        )
        self.empty_text.setWordWrap(True)
        self.empty_text.setObjectName("muted")
        layout.addWidget(self.empty_title)
        layout.addWidget(self.empty_text)
        layout.addStretch(1)
        layout.addSpacing(8)
        self.new_run = QPushButton("НОВОЕ ПРОХОЖДЕНИЕ")
        self.new_run.setIcon(IconProvider.icon(
            "common.add", 16, Colors.TEXT_PRIMARY
        ))
        self.new_run.setFixedHeight(36)
        self.new_run.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #34414D;"
            "border-radius:7px;color:#E9EDF1;font-weight:700;padding:7px 10px;}"
            "QPushButton:hover{background:#241437;border-color:#9B3CFF;"
            "color:#FFFFFF;} QPushButton:pressed{background:#321A4C;}"
        )
        self.new_run.clicked.connect(self.new_playthrough_requested.emit)
        layout.addWidget(self.new_run)
        return card

    def _build_detail(self) -> QFrame:
        detail = QFrame()
        detail.setObjectName("journeyStageDetail")
        detail.setMinimumHeight(Dimensions.JOURNEY_DETAIL_MIN_HEIGHT)
        detail.setMaximumHeight(Dimensions.JOURNEY_DETAIL_MAX_HEIGHT)
        detail.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        detail.setStyleSheet(
            "QFrame#journeyStageDetail{background:#0A1119;border:1px solid #26333E;"
            "border-radius:9px;}"
        )
        layout = QHBoxLayout(detail)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)
        overview = QFrame()
        overview.setStyleSheet("background:transparent;border:0;")
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(14)
        self.detail_title = QLabel()
        self.detail_title.setStyleSheet(
            "font-size:15pt;font-weight:800;color:white;"
        )
        self.detail_title.setWordWrap(True)
        self.stage_art = JourneyStageArtwork()
        self.stage_art.file_selected.connect(self._request_stage_media)
        overview_layout.addWidget(self.stage_art, 0, Qt.AlignmentFlag.AlignVCenter)
        stage_info = QFrame()
        stage_info.setStyleSheet("background:transparent;border:0;")
        stage_info_layout = QVBoxLayout(stage_info)
        stage_info_layout.setContentsMargins(0, 1, 0, 1)
        stage_info_layout.setSpacing(7)
        stage_info_layout.addWidget(self.detail_title)
        self.stage_status = QComboBox()
        self.stage_status.setFixedWidth(138)
        for value, label in (
            ("not_started", "Не начато"),
            ("current", "Текущее"),
            ("in_progress", "В процессе"),
            ("completed", "Завершено"),
        ):
            self.stage_status.addItem(label, value)
        self.stage_status.activated.connect(self._request_stage_state)
        self.stage_status.currentIndexChanged.connect(self._style_stage_status)
        self._style_stage_status(0)
        stage_info_layout.addWidget(self.stage_status, 0, Qt.AlignmentFlag.AlignLeft)
        self.rating_caption = QLabel("ОЦЕНКА ЭТАПА")
        self.rating_caption.setObjectName("caption")
        stage_info_layout.addWidget(self.rating_caption)
        self.stage_rating = VeloraRatingSelector()
        self.stage_rating.rating_changed.connect(self._request_stage_rating)
        stage_info_layout.addWidget(self.stage_rating, 0, Qt.AlignmentFlag.AlignLeft)
        stage_info_layout.addStretch(1)
        overview_layout.addWidget(stage_info, 1)
        layout.addWidget(overview, 55)
        layout.addWidget(self._vertical_separator())

        impressions = QFrame()
        impressions.setStyleSheet("background:transparent;border:0;")
        impressions_layout = QVBoxLayout(impressions)
        impressions_layout.setContentsMargins(0, 1, 0, 1)
        impressions_layout.setSpacing(8)
        self.preview_caption = QLabel("ВПЕЧАТЛЕНИЯ")
        self.preview_caption.setObjectName("caption")
        impressions_layout.addWidget(self.preview_caption)
        self.entry_preview = QLabel("Воспоминаний об этом этапе пока нет")
        self.entry_preview.setWordWrap(True)
        self.entry_preview.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.entry_preview.setMinimumHeight(44)
        self.entry_preview.setMaximumHeight(62)
        self.entry_preview.setStyleSheet(
            "color:#B7C1CB;background:transparent;border:0;padding:0;"
        )
        impressions_layout.addWidget(self.entry_preview)
        self.quick_impression_caption = QLabel("БЫСТРЫЕ ВПЕЧАТЛЕНИЯ")
        self.quick_impression_caption.setObjectName("caption")
        impressions_layout.addWidget(self.quick_impression_caption)
        quick_grid = QGridLayout()
        quick_grid.setContentsMargins(0, 0, 0, 0)
        quick_grid.setHorizontalSpacing(6)
        quick_grid.setVerticalSpacing(5)
        self.quick_impression_buttons: dict[str, QPushButton] = {}
        for index, label in enumerate(QUICK_STAGE_IMPRESSIONS):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(28)
            button.setStyleSheet(
                f"QPushButton{{background:{Colors.SURFACE_CARD};"
                f"color:{Colors.TEXT_SECONDARY};border:1px solid {Colors.BORDER_DEFAULT};"
                "border-radius:6px;padding:3px 8px;}"
                f"QPushButton:hover{{color:{Colors.TEXT_PRIMARY};"
                f"border-color:{Colors.BORDER_HOVER};background:{Colors.BACKGROUND_HOVER};}}"
                f"QPushButton:checked{{color:{Colors.TEXT_ON_ACCENT};"
                f"border-color:{Colors.BORDER_ACTIVE};background:{Colors.BACKGROUND_SELECTED};}}"
            )
            button.clicked.connect(
                lambda checked=False, value=label:
                self._add_quick_impression(value, checked)
            )
            quick_grid.addWidget(button, index // 3, index % 3)
            quick_grid.setColumnStretch(index % 3, 1)
            self.quick_impression_buttons[label] = button
        impressions_layout.addLayout(quick_grid)
        self.event_meta = QWidget()
        self.event_meta.setStyleSheet("background:transparent;border:0;")
        event_meta_layout = QHBoxLayout(self.event_meta)
        event_meta_layout.setContentsMargins(0, 0, 0, 0)
        event_meta_layout.setSpacing(7)
        self.event_rating = QLabel()
        self.event_mood = QLabel()
        event_meta_layout.addWidget(self.event_rating)
        event_meta_layout.addWidget(self.event_mood)
        event_meta_layout.addStretch()
        self.event_meta.hide()
        impressions_layout.addWidget(self.event_meta)
        self.event_actions = QHBoxLayout()
        self.edit_event = QPushButton("ИЗМЕНИТЬ")
        self.delete_event = QPushButton("УДАЛИТЬ")
        self.delete_event.setStyleSheet(
            f"QPushButton{{color:{Colors.DANGER};background:transparent;"
            f"border:1px solid {Colors.DANGER};border-radius:6px;padding:5px 9px;}}"
        )
        self.edit_event.clicked.connect(self._edit_selected_event)
        self.delete_event.clicked.connect(self._delete_selected_event)
        self.event_actions.addWidget(self.edit_event)
        self.event_actions.addWidget(self.delete_event)
        self.event_actions.addStretch()
        impressions_layout.addLayout(self.event_actions)
        self._set_event_actions_visible(False)
        impressions_layout.addStretch(1)
        layout.addWidget(impressions, 21)
        layout.addWidget(self._vertical_separator())

        right = QFrame()
        right.setMinimumWidth(580)
        right.setMaximumWidth(680)
        right.setStyleSheet("background:transparent;border:0;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 4)
        caption = QLabel("БЫСТРОЕ ДОБАВЛЕНИЕ")
        caption.setObjectName("caption")
        right_layout.addWidget(caption)
        actions = QGridLayout()
        actions.setSpacing(6)
        for column in range(4):
            actions.setColumnStretch(column, 1)
        for index, (kind, icon, text) in enumerate(EVENT_META):
            card = JourneyActionCard(kind, icon, text)
            card.activated.connect(
                lambda event_type, _label: self._open_entry_dialog(event_type)
            )
            actions.addWidget(card, index // 4, index % 4)
        right_layout.addLayout(actions)
        right_layout.addStretch()
        self.material_count = QLabel()
        self.material_count.setObjectName("muted")
        self.material_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        # Kept as a presentation value for compatibility, but the quick-add
        # panel must stay focused on actions rather than repeat event totals.
        self.material_count.setVisible(False)
        layout.addWidget(right, 13)
        return detail

    @staticmethod
    def _vertical_separator() -> QFrame:
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background:#26333E;border:0;")
        return separator

    def _build_analytics(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("journeyAnalytics")
        panel.setMinimumHeight(Dimensions.JOURNEY_ANALYTICS_MIN_HEIGHT)
        panel.setMaximumHeight(Dimensions.JOURNEY_ANALYTICS_MAX_HEIGHT)
        panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        panel.setStyleSheet(
            "QFrame#journeyAnalytics{background:#0B121A;border:1px solid #26333E;"
            "border-radius:9px;}"
        )
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)
        stats = QVBoxLayout()
        title = QLabel("СТАТИСТИКА ПРОХОЖДЕНИЯ")
        title.setObjectName("caption")
        stats.addWidget(title)
        metrics = QHBoxLayout()
        metrics.setSpacing(Spacing.SPACE_12)
        self.metric_values: dict[str, QLabel] = {}
        metric_definitions = (
            ("favorite", "Любимые"),
            ("difficult", "Сложные"),
            ("notes", "Заметки"),
            ("events", "События"),
            ("screenshots", "Скриншоты"),
        )
        for index, (key, caption) in enumerate(metric_definitions):
            box = QVBoxLayout()
            box.setSpacing(Spacing.SPACE_4)
            value = QLabel("0")
            value.setStyleSheet(
                f"{Typography.METRIC_MEDIUM}color:{Colors.TEXT_PRIMARY};border:0;"
            )
            label = QLabel(caption)
            label.setObjectName("muted")
            self.metric_values[key] = value
            box.addWidget(value)
            box.addWidget(label)
            metrics.addLayout(box)
            if index < len(metric_definitions) - 1:
                divider = QFrame()
                divider.setObjectName("journeyMetricDivider")
                divider.setFixedSize(1, 42)
                divider.setStyleSheet(
                    f"background:{Colors.BORDER_SUBTLE};border:0;"
                )
                metrics.addWidget(divider, 0, Qt.AlignmentFlag.AlignVCenter)
        metrics.addStretch()
        stats.addLayout(metrics)
        layout.addLayout(stats, 3)
        graph_box = QVBoxLayout()
        graph_title = QLabel("ГРАФИК НАСТРОЕНИЯ")
        graph_title.setObjectName("caption")
        graph_box.addWidget(graph_title)
        self.graph = JourneyMoodGraph()
        graph_box.addWidget(self.graph)
        layout.addLayout(graph_box, 5)
        score = QVBoxLayout()
        score_title = QLabel("ИТОГОВАЯ ОЦЕНКА (ПРЕДВАРИТЕЛЬНО)")
        score_title.setObjectName("caption")
        self.score_value = QLabel("—")
        self.score_value.setStyleSheet(
            f"font-size:26pt;font-weight:900;color:{SUCCESS};border:0;"
        )
        self.score_stars = QLabel("☆☆☆☆☆")
        self.score_stars.setStyleSheet(
            f"font-size:18pt;font-weight:700;color:{SUCCESS};border:0;"
        )
        self.score_quality = QLabel("")
        self.score_quality.setStyleSheet(
            f"font-size:10pt;font-weight:700;color:{SUCCESS};border:0;"
        )
        self.score_caption = QLabel("На основе заполненных этапов")
        self.score_caption.setObjectName("muted")
        score_line = QHBoxLayout()
        score_line.setContentsMargins(0, 0, 0, 0)
        score_line.setSpacing(10)
        score_line.addWidget(self.score_value, 0, Qt.AlignmentFlag.AlignVCenter)
        score_line.addWidget(self.score_stars, 0, Qt.AlignmentFlag.AlignVCenter)
        score_line.addWidget(self.score_quality, 0, Qt.AlignmentFlag.AlignVCenter)
        score_line.addStretch()
        score.addWidget(score_title)
        score.addLayout(score_line)
        score.addWidget(self.score_caption)
        score.addStretch()
        layout.addLayout(score, 2)
        return panel

    def set_presentation(self, model: JourneyPresentation) -> None:
        old_selection = self._selected_stage_id
        old_event_selection = self._selected_event_id
        old_scroll = self.timeline_scroll.horizontalScrollBar().value()
        # A still-running navigation animation must not overwrite the position
        # restored after a data refresh (for example, after saving a rating).
        if self._scroll_animation is not None:
            self._scroll_animation.stop()
            self._scroll_animation = None
        self._route_render_generation = getattr(
            self, "_route_render_generation", 0
        ) + 1
        render_generation = self._route_render_generation
        self._pending_route_scroll = (old_scroll, render_generation)
        self._model = model
        self._selected_stage_id = (
            old_selection if old_selection and any(
                stage.stage_id == old_selection for stage in model.stages
            ) else self._active_stage_id(model.stages, model.status)
        )
        self._render_run_card(model)
        self._render_route(model)
        self._render_selected_stage()
        if old_event_selection:
            event = next(
                (entry for stage in model.stages for entry in stage.entries
                 if entry.source_id == old_event_selection), None,
            )
            if event is not None:
                self._select_event(event)
        self._render_analytics(model)
        self.timeline_scroll.horizontalScrollBar().setValue(old_scroll)
        if old_selection is None:
            self._ensure_selected_visible()
        else:
            # Rebuilding the route briefly resets the scrollbar range to zero.
            # Restore after Qt has recalculated the new content width, otherwise
            # saving a rating makes the whole Journey jump back to its start.
            QTimer.singleShot(
                0,
                lambda value=old_scroll, generation=render_generation:
                self._restore_route_position(value, generation),
            )

    def set_editable(self, editable: bool) -> None:
        self._editable = editable
        self.stage_rating.setEnabled(editable)
        self.stage_status.setEnabled(editable)
        self.stage_art.setEnabled(editable)

    def _render_run_card(self, model: JourneyPresentation) -> None:
        self.run_selector.blockSignals(True)
        self.run_selector.clear()
        # sequence_no is a storage/history identifier and may contain gaps
        # after legacy deletes (for example 1, 2, 10).  The selector presents
        # the quantitative order of the existing runs instead: 1, 2, 3.
        for display_number, option in enumerate(model.playthrough_options, 1):
            self.run_selector.addItem(
                f"ПРОХОЖДЕНИЕ №{display_number}", option.playthrough_id
            )
        index = self.run_selector.findData(model.playthrough_id)
        self.run_selector.setCurrentIndex(max(0, index))
        self.run_selector.blockSignals(False)
        has_runs = bool(model.playthrough_options)
        for widget in (
            self.run_kind, self.run_divider,
            *self.run_metrics.values(),
        ):
            widget.setVisible(has_runs)
        self.run_selector_group.setVisible(has_runs)
        metric_labels = [
            child for child in self.run_card.findChildren(QLabel)
            if child.objectName() == "caption"
        ]
        for label in metric_labels:
            label.setVisible(has_runs)
        self.empty_title.setVisible(not has_runs)
        self.empty_text.setVisible(not has_runs)
        self.new_run.setText(
            "НОВОЕ ПРОХОЖДЕНИЕ" if has_runs else "НАЧАТЬ ПРОХОЖДЕНИЕ"
        )
        if not has_runs:
            return
        sequence = model.playthrough_sequence or 1
        self.run_kind.setText(
            "Текущее"
            if next(
                (
                    option.is_current for option in model.playthrough_options
                    if option.playthrough_id == model.playthrough_id
                ),
                False,
            )
            else "Первое прохождение" if sequence == 1
            else "Повторное прохождение"
        )
        completed = self._completed_stage_ids(model.stages, model.status)
        self.run_metrics["status"].setText(
            RUN_STATUS_LABELS.get(model.status, "Не начато")
        )
        self.run_metrics["progress"].setText(f"{len(completed)} из {len(model.stages)} этапов")
        self.run_metrics["started"].setText(_date(model.started_at))
        self.run_metrics["last_activity"].setText(_date(model.last_activity_at))

    def _render_route(self, model: JourneyPresentation) -> None:
        self._clear_layout(self.route)
        self._stage_buttons.clear()
        completed = self._completed_stage_ids(model.stages, model.status)
        self.progress.setText(f"{len(completed)} из {len(model.stages)} этапов")
        segments = JourneyTimelineLayoutModel.build(model.stages)
        for index, (stage, segment) in enumerate(zip(model.stages, segments), start=1):
            state = {
                "completed": "complete", "current": "active",
                "in_progress": "progress", "skipped": "future",
                "not_started": "future",
            }.get(stage.state, "future")
            stage_host = QWidget()
            stage_host.setFixedWidth(Dimensions.JOURNEY_COMPACT_STAGE_WIDTH)
            stage_host.setFixedHeight(
                Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT
                + Dimensions.JOURNEY_EVENT_AREA_HEIGHT
            )
            stage_host.setStyleSheet("background:transparent;border:0;")
            column = QVBoxLayout(stage_host)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(Spacing.SPACE_12)
            button = JourneyTimelineNode(stage, state, index)
            button.stage_selected.connect(self._select_stage)
            button.stage_state_requested.connect(self.stage_state_requested.emit)
            button.stage_open_requested.connect(self._open_stage_dialog)
            button.stage_favorite_requested.connect(self.stage_favorite_requested.emit)
            button.set_selected(stage.stage_id == self._selected_stage_id)
            self._stage_buttons[stage.stage_id] = button
            column.addWidget(button)
            marker_host = QFrame()
            marker_host.setFixedWidth(Dimensions.JOURNEY_STAGE_CARD_WIDTH)
            marker_host.setMinimumHeight(100)
            marker_host.setMaximumHeight(Dimensions.JOURNEY_EVENT_AREA_HEIGHT)
            marker_host.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
            marker_host.setStyleSheet("QFrame{background:transparent;border:0;}")
            marker_layout = QVBoxLayout(marker_host)
            marker_layout.setContentsMargins(0, 0, 0, 0)
            marker_layout.setSpacing(2)
            marker_layout.addSpacing(25)
            marker_layout.addStretch()
            column.addWidget(marker_host)
            self.route.addWidget(stage_host, 0, Qt.AlignmentFlag.AlignTop)
            visible_entries = self._prioritized_entries(stage)
            event_segment = QWidget()
            event_segment.setFixedWidth(segment.width)
            event_segment.setFixedHeight(
                Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT
                + Dimensions.JOURNEY_EVENT_AREA_HEIGHT
            )
            event_segment.setStyleSheet("background:transparent;border:0;")
            event_column = QVBoxLayout(event_segment)
            event_column.setContentsMargins(
                0, Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT + 21, 0, 0
            )
            event_row = QHBoxLayout()
            event_row.setContentsMargins(0, 0, 0, 0)
            event_row.setSpacing(0)
            for entry in visible_entries[:JourneyTimelineLayoutModel.MAX_VISIBLE_EVENTS]:
                marker = JourneyEventMarker(entry)
                marker.selected.connect(self._select_event)
                event_row.addWidget(marker, 1)
            if segment.hidden_event_count:
                more = QPushButton(f"+{segment.hidden_event_count}")
                more.setFixedWidth(JourneyTimelineLayoutModel.OVERFLOW_SLOT_WIDTH)
                more.setToolTip("Остальные события этапа")
                more.clicked.connect(
                    lambda checked=False, entries=tuple(
                        visible_entries[JourneyTimelineLayoutModel.MAX_VISIBLE_EVENTS:]
                    ),
                    anchor=more: self._open_event_group_menu(entries, anchor)
                )
                event_row.addWidget(more)
            event_column.addLayout(event_row)
            event_column.addStretch()
            self.route.addWidget(event_segment, 0, Qt.AlignmentFlag.AlignTop)
        self.route.addStretch()
        self.route.activate()
        route_spacing = self.route.spacing()
        route_margins = self.route.contentsMargins()
        fixed_widgets = len(segments) * 2
        route_width = (
            route_margins.left() + route_margins.right()
            + sum(
                Dimensions.JOURNEY_COMPACT_STAGE_WIDTH + segment.width
                for segment in segments
            )
            + max(0, fixed_widgets - 1) * route_spacing
        )
        # Give QScrollArea a stable content extent immediately.  Without this,
        # clearing/rebuilding the route transiently reports a zero range and
        # Qt snaps the viewport to the first stage.
        self.timeline_host.setMinimumWidth(route_width)
        route_height = (
            Dimensions.JOURNEY_COMPACT_STAGE_HEIGHT
            + Dimensions.JOURNEY_EVENT_AREA_HEIGHT
            + 16
        )
        self.timeline_host.setFixedHeight(route_height)
        self.timeline_canvas.setGeometry(
            2, 3, route_width, self.timeline_scroll.height() - 6
        )
        # Do not sample QWidget geometry while QScrollArea is still laying out
        # newly inserted children.  Intermediate positions caused a row of
        # phantom dots and detached the route line from its stage cards.
        centers_list: list[int] = []
        cursor = route_margins.left()
        for segment in segments:
            centers_list.append(
                cursor + Dimensions.JOURNEY_COMPACT_STAGE_WIDTH // 2
            )
            cursor += (
                Dimensions.JOURNEY_COMPACT_STAGE_WIDTH
                + route_spacing
                + segment.width
                + route_spacing
            )
        centers = tuple(centers_list)
        line_end = centers[-1] if centers else None
        if centers and segments:
            last_segment = segments[-1]
            if last_segment.visible_event_count:
                last_stage_left = centers[-1] - (
                    Dimensions.JOURNEY_COMPACT_STAGE_WIDTH // 2
                )
                event_start = (
                    last_stage_left + Dimensions.JOURNEY_COMPACT_STAGE_WIDTH
                    + route_spacing
                )
                if last_segment.hidden_event_count:
                    line_end = (
                        event_start
                        + last_segment.visible_event_count
                        * JourneyTimelineLayoutModel.EVENT_SLOT_WIDTH
                        + JourneyTimelineLayoutModel.OVERFLOW_SLOT_WIDTH // 2
                    )
                else:
                    line_end = (
                        event_start
                        + (last_segment.visible_event_count - 1)
                        * JourneyTimelineLayoutModel.EVENT_SLOT_WIDTH
                        + JourneyTimelineLayoutModel.EVENT_SLOT_WIDTH // 2
                    )
        self.timeline_canvas.set_route(
            (stage.state for stage in model.stages),
            next((i for i, stage in enumerate(model.stages)
                  if stage.stage_id == self._selected_stage_id), -1),
            centers,
            line_end,
        )
        self.timeline_canvas.lower()
        self.timeline_scroll.verticalScrollBar().setValue(0)
        self._update_route_arrows()

    @staticmethod
    def _completed_stage_ids(
        stages: Iterable[JourneyStage], status: str | None,
    ) -> set[str]:
        stages = tuple(stages)
        return {stage.stage_id for stage in stages if stage.state == "completed"}

    @staticmethod
    def _active_stage_id(
        stages: Iterable[JourneyStage], status: str | None,
    ) -> str:
        stages = tuple(stages)
        if not stages:
            return ""
        explicit = next(
            (stage.stage_id for stage in stages
             if stage.state in ("current", "in_progress")), None,
        )
        if explicit:
            return explicit
        return next(
            (stage.stage_id for stage in stages if stage.state != "completed"),
            stages[-1].stage_id,
        )

    def _select_stage(self, stage_id: str) -> None:
        self._selected_stage_id = stage_id
        self._selected_event_id = None
        for key, button in self._stage_buttons.items():
            button.set_selected(key == stage_id)
        self._render_selected_stage()
        self._ensure_selected_visible()
        self.stage_selection_changed.emit(stage_id)

    def _select_event(self, entry: JourneyEntry) -> None:
        self._selected_stage_id = entry.stage_id
        self._selected_event_id = entry.source_id
        for key, button in self._stage_buttons.items():
            button.set_selected(key == entry.stage_id)
        self.detail_title.setText(entry.title)
        # Lifecycle state belongs to the mission tile, never to an event.
        self.stage_status.hide()
        self.rating_caption.setText("ОЦЕНКА СОБЫТИЯ")
        self.stage_rating.setEnabled(self._editable)
        self.stage_rating.blockSignals(True)
        self.stage_rating.setValue(entry.rating)
        self.stage_rating.blockSignals(False)
        self._set_quick_impressions_visible(False)
        self.stage_art.set_path(entry.media_path)
        self.preview_caption.setText(JourneyEventMarker.heading_text(entry))
        self.entry_preview.setText(entry.body or "Описание не добавлено")
        self.material_count.setText("СОБЫТИЕ JOURNEY")
        self._render_event_meta(entry)
        self._set_event_actions_visible(True)

    def _render_event_meta(self, entry: JourneyEntry | None) -> None:
        if entry is None:
            self.event_meta.hide()
            self.event_rating.clear()
            self.event_mood.clear()
            return
        has_rating = entry.rating is not None
        mood = MoodRegistry.get(entry.mood_id)
        self.event_rating.setVisible(has_rating)
        if has_rating:
            self.event_rating.setText(f"Оценка события: {entry.rating:.1f}")
            self.event_rating.setStyleSheet(
                f"color:{rating_color(entry.rating)};font-weight:700;border:0;"
            )
        self.event_mood.setVisible(mood is not None)
        if mood is not None:
            self.event_mood.setPixmap(IconProvider.pixmap(
                mood.icon_key, Dimensions.ICON_MEDIUM, mood.color
            ))
            self.event_mood.setToolTip(mood.display_name)
        self.event_meta.setVisible(has_rating or mood is not None)

    def _select_event_group(self, entries: tuple[JourneyEntry, ...]) -> None:
        if not entries:
            return
        self._selected_stage_id = entries[0].stage_id
        self._selected_event_id = None
        self.detail_title.setText("СОБЫТИЯ ЭТАПА")
        self.stage_status.hide()
        self.rating_caption.setText("ОЦЕНКА СОБЫТИЯ")
        self.stage_rating.blockSignals(True)
        self.stage_rating.setValue(None)
        self.stage_rating.blockSignals(False)
        self.stage_rating.setEnabled(False)
        self._set_quick_impressions_visible(False)
        self.stage_art.set_path(None)
        self.preview_caption.setText("СОБЫТИЯ ЭТАПА")
        self.entry_preview.setText("\n".join(
            f"{entry.title} — {entry.body}".rstrip(" —") for entry in entries
        ))
        self.material_count.setText("ГРУППА СОБЫТИЙ")
        self._render_event_meta(None)
        self._set_event_actions_visible(False)

    def _open_event_group_menu(
        self, entries: tuple[JourneyEntry, ...], anchor: QWidget,
    ) -> None:
        """Let the user choose a concrete event hidden behind the +N marker."""
        if not entries:
            return
        self._select_event_group(entries)
        menu = QMenu(anchor)
        menu.setStyleSheet(
            "QMenu{min-width:260px;padding:5px;}"
            "QMenu::item{min-height:24px;padding:6px 18px 6px 10px;}"
        )
        for entry in entries:
            action = menu.addAction(
                IconProvider.icon(
                    JourneyEventMarker.icon_key(entry), Dimensions.ICON_SMALL,
                    JourneyEventMarker.color(entry),
                ),
                entry.title or "Событие Journey",
            )
            action.triggered.connect(
                lambda checked=False, selected=entry: self._select_event(selected)
            )
        self._event_group_menu = menu
        menu.popup(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _set_event_actions_visible(self, visible: bool) -> None:
        self.edit_event.setVisible(visible and self._editable)
        self.delete_event.setVisible(visible and self._editable)

    def _set_quick_impressions_visible(self, visible: bool) -> None:
        self.quick_impression_caption.setVisible(visible)
        for button in self.quick_impression_buttons.values():
            button.setVisible(visible)

    def _selected_event(self) -> JourneyEntry | None:
        if self._model is None or self._selected_event_id is None:
            return None
        return next((entry for stage in self._model.stages for entry in stage.entries
                     if entry.source_id == self._selected_event_id), None)

    def _edit_selected_event(self) -> None:
        entry = self._selected_event()
        if entry is None or self._model is None:
            return
        stage = next(stage for stage in self._model.stages if stage.stage_id == entry.stage_id)
        dialog = JourneyEntryDialog(
            stage, entry.kind, self._model.stages.index(stage) + 1, self,
            entry=entry,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.event_revision_requested.emit((entry.source_id, dialog.draft()))

    def _delete_selected_event(self) -> None:
        entry = self._selected_event()
        if entry is None:
            return
        if QMessageBox.question(
            self, "Удалить событие", f"Удалить «{entry.title}»?",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        ) == QMessageBox.StandardButton.Yes:
            self.event_delete_requested.emit(entry.source_id)

    @staticmethod
    def _prioritized_entries(stage: JourneyStage) -> list[JourneyEntry]:
        entries = [entry for entry in stage.entries if entry.kind != "rating"]
        return sorted(
            entries,
            key=lambda entry: (
                JourneyView._event_time_key(entry.occurred_at), entry.source_id
            ),
        )

    @staticmethod
    def _event_time_key(value: str) -> tuple[int, object]:
        parsed = QDateTime.fromString(value, Qt.DateFormat.ISODate)
        if parsed.isValid():
            return (0, parsed.toMSecsSinceEpoch())
        return (1, value)

    def _open_stage_dialog(self, stage_id: str) -> None:
        self._select_stage(stage_id)
        if not self._editable or self._model is None:
            return
        menu = QMenu(self)
        menu.setTitle("Добавить в этап")
        state_menu = menu.addMenu(
            IconProvider.icon(
                "status.current", Dimensions.ICON_SMALL, Colors.ACCENT_PRIMARY
            ),
            "Уточнить состояние",
        )
        stage = next(
            item for item in self._model.stages if item.stage_id == stage_id
        )
        for value, label, icon_key, color in (
            ("not_started", "Не начато", "status.not_started", Colors.STATUS_NOT_STARTED),
            ("current", "Текущее", "status.current", Colors.STATUS_CURRENT),
            ("in_progress", "В процессе", "status.in_progress", Colors.STATUS_IN_PROGRESS),
            ("completed", "Завершено", "status.completed", Colors.STATUS_COMPLETED),
        ):
            action = state_menu.addAction(
                IconProvider.icon(icon_key, Dimensions.ICON_SMALL, color), label
            )
            action.setCheckable(True)
            action.setChecked(stage.state == value)
            action.triggered.connect(
                lambda checked=False, state=value:
                self.stage_state_requested.emit(stage_id, state)
            )
        self._stage_state_menu = state_menu
        menu.addSeparator()
        for event_type, icon_key, label in EVENT_META:
            action = menu.addAction(
                IconProvider.icon(
                    icon_key, Dimensions.ICON_SMALL, Colors.ACCENT_PRIMARY
                ),
                label,
            )
            action.triggered.connect(
                lambda checked=False, kind=event_type:
                self._open_entry_dialog(kind)
            )
        self._entry_type_menu = menu
        card = self._stage_buttons.get(stage_id)
        anchor = (
            card.mapToGlobal(QPoint(0, card.height() + 4))
            if card is not None else QCursor.pos()
        )
        menu.popup(anchor)

    def _request_stage_rating(self, value: float | None) -> None:
        if not self._editable or value is None:
            return
        entry = self._selected_event()
        if entry is not None:
            draft = JourneyEntryDraft(
                stage_id=entry.stage_id or self._selected_stage_id or "",
                event_type=entry.kind,
                title=entry.title,
                body=entry.body,
                tags=entry.tags,
                mood_id=entry.mood_id,
                rating=float(value),
                occurred_at=entry.occurred_at,
                metadata={"file_path": entry.media_path or ""},
            )
            self.event_revision_requested.emit((entry.source_id, draft))
            return
        if self._selected_stage_id:
            self.stage_rating_requested.emit(self._selected_stage_id, float(value))

    def _request_stage_state(self, index: int) -> None:
        if self._editable and self._selected_stage_id and index >= 0:
            self.stage_state_requested.emit(
                self._selected_stage_id,
                str(self.stage_status.itemData(index)),
            )

    def _style_stage_status(self, index: int) -> None:
        state = str(self.stage_status.itemData(index) or "not_started")
        color = {
            "current": Colors.STATUS_CURRENT,
            "in_progress": Colors.STATUS_IN_PROGRESS,
            "completed": Colors.STATUS_COMPLETED,
        }.get(state, Colors.STATUS_NOT_STARTED)
        self.stage_status.setStyleSheet(
            f"QComboBox{{background:{Colors.SURFACE_CARD};color:{color};"
            f"border:1px solid {color};border-radius:6px;padding:5px 24px 5px 9px;"
            "font-weight:700;}"
            f"QComboBox:hover{{background:{Colors.BACKGROUND_HOVER};}}"
            "QComboBox::drop-down{background:transparent;border:0;width:22px;"
            "subcontrol-origin:padding;subcontrol-position:center right;}"
            f"QComboBox QAbstractItemView{{background:{Colors.SURFACE_CARD};"
            f"color:{Colors.TEXT_PRIMARY};border:1px solid {Colors.BORDER_DEFAULT};"
            f"selection-background-color:{Colors.BACKGROUND_SELECTED};}}"
        )

    def _request_stage_media(self, path: str) -> None:
        if self._editable and self._selected_stage_id:
            self.stage_media_requested.emit(self._selected_stage_id, path)

    def _open_entry_dialog(self, event_type: str) -> None:
        if not self._editable or self._model is None or not self._selected_stage_id:
            return
        stage = next(
            item for item in self._model.stages
            if item.stage_id == self._selected_stage_id
        )
        number = self._model.stages.index(stage) + 1
        dialog = JourneyEntryDialog(stage, event_type, number, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.entry_requested.emit(dialog.draft())

    def _ensure_selected_visible(self) -> None:
        button = self._stage_buttons.get(self._selected_stage_id or "")
        if button is not None:
            viewport_width = self.timeline_scroll.viewport().width()
            target = max(
                0,
                button.mapTo(self.timeline_host, button.rect().center()).x()
                - viewport_width // 2,
            )
            self._animate_route_to(target)

    def _move_route(self, direction: int) -> None:
        """Move by one chapter card and keep keyboard/mouse navigation equal."""
        bar = self.timeline_scroll.horizontalScrollBar()
        self._animate_route_to(bar.value() + direction * 215)

    def _restore_route_position(self, value: int, generation: int) -> None:
        if generation != getattr(self, "_route_render_generation", 0):
            return
        bar = self.timeline_scroll.horizontalScrollBar()
        if value > bar.minimum() and bar.maximum() <= bar.minimum():
            return
        self._pending_route_scroll = None
        bar.setValue(max(bar.minimum(), min(bar.maximum(), int(value))))
        self._update_route_arrows()

    def _update_route_arrows(self, *_args) -> None:
        bar = self.timeline_scroll.horizontalScrollBar()
        pending = getattr(self, "_pending_route_scroll", None)
        if pending is not None and bar.maximum() > bar.minimum():
            self._restore_route_position(*pending)
            return
        has_overflow = bar.maximum() > bar.minimum()
        can_move_left = has_overflow and bar.value() > bar.minimum()
        can_move_right = has_overflow and bar.value() < bar.maximum()
        self.route_previous.setVisible(can_move_left)
        self.route_previous.setEnabled(can_move_left)
        self.route_next.setVisible(can_move_right)
        self.route_next.setEnabled(can_move_right)

    def _animate_route_to(self, target: int) -> None:
        bar = self.timeline_scroll.horizontalScrollBar()
        bounded = max(bar.minimum(), min(bar.maximum(), int(target)))
        if self._scroll_animation is not None:
            self._scroll_animation.stop()
        animation = QPropertyAnimation(bar, b"value", self)
        animation.setDuration(220)
        animation.setStartValue(bar.value())
        animation.setEndValue(bounded)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation = animation
        animation.start()

    def _render_selected_stage(self) -> None:
        if self._model is None or not self._model.stages:
            return
        self._render_event_meta(None)
        stage = next(
            item for item in self._model.stages
            if item.stage_id == self._selected_stage_id
        )
        index = self._model.stages.index(stage) + 1
        self._selected_event_id = None
        self.rating_caption.setText("ОЦЕНКА ЭТАПА")
        self.stage_rating.setEnabled(self._editable)
        self._set_event_actions_visible(False)
        self.preview_caption.setText("ВПЕЧАТЛЕНИЯ")
        self.detail_title.setText(f"{index:02d}  {stage.title}")
        self.stage_status.show()
        self._set_quick_impressions_visible(True)
        self.material_count.setText(
            f"{JourneyTimelineLayoutModel.count_events(stage)} событий"
        )
        self.stage_status.blockSignals(True)
        status_index = self.stage_status.findData(stage.state)
        self.stage_status.setCurrentIndex(max(0, status_index))
        self.stage_status.blockSignals(False)
        self._style_stage_status(self.stage_status.currentIndex())
        self.stage_art.set_path(stage.media_path)
        rating = _latest_rating(stage)
        self.stage_rating.blockSignals(True)
        self.stage_rating.setValue(rating)
        self.stage_rating.blockSignals(False)
        latest = next(
            (entry for entry in reversed(stage.entries)
             if entry.body or entry.title), None,
        )
        self.entry_preview.setText(
            (latest.body or latest.title) if latest is not None
            else "Воспоминаний об этом этапе пока нет"
        )
        stored_impressions = {
            entry.title.casefold() for entry in stage.entries
            if entry.kind == "impression"
        }
        for label, button in self.quick_impression_buttons.items():
            button.blockSignals(True)
            button.setChecked(label.casefold() in stored_impressions)
            button.blockSignals(False)

    def _add_quick_impression(self, label: str, checked: bool) -> None:
        if not checked or not self._editable or not self._selected_stage_id:
            button = self.quick_impression_buttons.get(label)
            if button is not None and not checked:
                button.setChecked(True)
            return
        if self._model is None:
            return
        stage = next(
            (item for item in self._model.stages
             if item.stage_id == self._selected_stage_id),
            None,
        )
        if stage is None:
            return
        if any(
            entry.kind == "impression"
            and entry.title.casefold() == label.casefold()
            for entry in stage.entries
        ):
            return
        self.entry_requested.emit(JourneyEntryDraft(
            stage_id=stage.stage_id,
            event_type="impression",
            title=label,
            body="",
            occurred_at=datetime.now().isoformat(timespec="seconds"),
            metadata={"quick_impression": True},
        ))

    def _render_analytics(self, model: JourneyPresentation) -> None:
        ratings = tuple(_latest_rating(stage) for stage in model.stages)
        values = tuple(
            value for value in ratings
            if value is not None and 1 <= value <= 10
        )
        invalid = tuple(
            value for value in ratings
            if value is not None and not 1 <= value <= 10
        )
        if invalid:
            LOGGER.warning(
                "Journey ignored invalid stage ratings: count=%s",
                len(invalid),
            )
        visible_entries = tuple(
            entry for stage in model.stages for entry in stage.entries
            if entry.kind in JourneyTimelineLayoutModel.VISIBLE_TYPES
        )
        notes = sum(1 for entry in visible_entries if entry.kind == "note")
        screenshots = sum(
            1 for entry in visible_entries if entry.kind == "screenshot"
        )
        self.metric_values["favorite"].setText(
            str(sum(1 for stage in model.stages if stage.favorite))
        )
        self.metric_values["difficult"].setText(
            str(sum(1 for stage in model.stages if stage.difficult))
        )
        self.metric_values["notes"].setText(str(notes))
        self.metric_values["events"].setText(str(len(visible_entries)))
        self.metric_values["screenshots"].setText(str(screenshots))
        graph_points: list[MoodChartPoint] = []
        for index, (stage, value) in enumerate(zip(model.stages, ratings), 1):
            graph_points.append(MoodChartPoint(
                index,
                mood_id=stage.mood_id,
                rating=value,
                selected=stage.stage_id == self._selected_stage_id,
                label=f"{index:02d}",
            ))
            rated_events = sorted(
                (
                    entry for entry in stage.entries
                    if entry.kind != "rating" and entry.rating is not None
                ),
                key=lambda entry: (entry.occurred_at, entry.source_id),
            )
            graph_points.extend(
                MoodChartPoint(
                    index,
                    mood_id=entry.mood_id,
                    rating=entry.rating,
                    label=entry.title,
                    is_event=True,
                )
                for entry in rated_events
            )
        self.graph.set_points(graph_points)
        if values:
            score = sum(values) / len(values)
            color = rating_color(score)
            self.score_value.setText(f"{score:.1f}")
            filled_stars = max(1, min(5, round(score / 2)))
            self.score_stars.setText(
                "★" * filled_stars + "☆" * (5 - filled_stars)
            )
            self.score_quality.setText(_rating_verdict(score))
            self.score_value.setStyleSheet(
                f"font-size:26pt;font-weight:900;color:{color};border:0;"
            )
            self.score_stars.setStyleSheet(
                f"font-size:18pt;font-weight:700;color:{color};border:0;"
            )
            self.score_quality.setStyleSheet(
                f"font-size:10pt;font-weight:700;color:{color};border:0;"
            )
            self.score_caption.setText(
                f"На основе {len(values)} из {len(ratings)} заполненных этапов"
            )
        else:
            self.score_value.setText("—")
            self.score_stars.setText("☆☆☆☆☆")
            self.score_quality.setText("Не оценено")
            muted = Colors.TEXT_DISABLED
            self.score_value.setStyleSheet(
                f"font-size:26pt;font-weight:900;color:{muted};border:0;"
            )
            self.score_stars.setStyleSheet(
                f"font-size:18pt;font-weight:700;color:{muted};border:0;"
            )
            self.score_quality.setStyleSheet(
                f"font-size:10pt;font-weight:700;color:{muted};border:0;"
            )
            self.score_caption.setText("Этапы ещё не оценены")

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            if self._model and self._model.stages:
                ids = [stage.stage_id for stage in self._model.stages]
                current = ids.index(self._selected_stage_id or ids[0])
                offset = -1 if event.key() == Qt.Key.Key_Left else 1
                self._select_stage(ids[max(0, min(len(ids) - 1, current + offset))])
            event.accept()
            return
        super().keyPressEvent(event)

    @classmethod
    def _clear_layout(cls, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                cls._clear_layout(item.layout())
