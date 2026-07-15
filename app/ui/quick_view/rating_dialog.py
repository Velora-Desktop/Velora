from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from app.core.icon_registry import IconRegistry


GAME_CRITERIA = (
    ("Графика", "graphics.svg"), ("Саундтрек", "soundtrack.svg"),
    ("Сюжет", "story.svg"), ("Геймплей", "gameplay.svg"),
    ("Атмосфера", "atmosphere.svg"),
)

CRITERIA_BY_MEDIA = {
    "Игры": GAME_CRITERIA,
    "Фильмы": (("Сюжет", "story.svg"), ("Актёрская игра", "atmosphere.svg"), ("Режиссура", "gameplay.svg"), ("Саундтрек", "soundtrack.svg"), ("Визуал", "graphics.svg")),
    "Сериалы": (("Сюжет", "story.svg"), ("Персонажи", "atmosphere.svg"), ("Темп", "gameplay.svg"), ("Саундтрек", "soundtrack.svg"), ("Визуал", "graphics.svg")),
    "Программы": (("Функциональность", "gameplay.svg"), ("Удобство", "atmosphere.svg"), ("Интерфейс", "graphics.svg"), ("Стабильность", "story.svg"), ("Производительность", "soundtrack.svg")),
}


def request_rating(
    current: dict[str, int],
    parent=None,
    media_type: str = "Игры",
    current_hours: float = 0.0,
) -> tuple[dict[str, int], float] | None:
    dialog=QDialog(parent); dialog.setWindowTitle("Моя оценка"); dialog.setWindowIcon(IconRegistry.icon("edit", category="ui")); dialog.setMinimumWidth(640)
    root=QVBoxLayout(dialog); root.setContentsMargins(22,18,22,18); root.setSpacing(12)
    title=QLabel("ОЦЕНИТЕ ОБЪЕКТ"); title.setStyleSheet("font-size:17pt;font-weight:700;"); root.addWidget(title)
    hint=QLabel("Перемещайте ползунки от 1 до 10. Средняя оценка рассчитывается сразу."); hint.setObjectName("muted"); root.addWidget(hint)
    editors={}; values={}
    for name,icon_name in CRITERIA_BY_MEDIA.get(media_type, GAME_CRITERIA):
        row=QWidget(); layout=QHBoxLayout(row); layout.setContentsMargins(0,4,0,4); layout.setSpacing(12)
        icon=QLabel(); icon.setFixedSize(28,28); icon.setPixmap(IconRegistry.pixmap(icon_name.removesuffix(".svg"),22,variant="svg",category="rating")); layout.addWidget(icon)
        label=QLabel(name); label.setMinimumWidth(105); label.setStyleSheet("font-size:11pt;font-weight:550;"); layout.addWidget(label)
        slider=QSlider(Qt.Orientation.Horizontal); slider.setRange(1,10); slider.setValue(current.get(name,5)); slider.setMinimumWidth(330)
        slider.setStyleSheet("QSlider::groove:horizontal{height:7px;background:#252C35;border-radius:3px;}QSlider::sub-page:horizontal{background:#8B2CF5;border-radius:3px;}QSlider::handle:horizontal{width:18px;margin:-6px 0;background:#E7D7FF;border:2px solid #9D4CFF;border-radius:9px;}")
        layout.addWidget(slider,1)
        value=QLabel(); value.setFixedWidth(58); value.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(value)
        editors[name]=slider; values[name]=value; root.addWidget(row)
    average_box=QWidget(); average_box.setStyleSheet("background:#101923;border:1px solid #293844;border-radius:8px;"); average_layout=QHBoxLayout(average_box)
    average_layout.addWidget(QLabel("СРЕДНЯЯ ОЦЕНКА")); average_layout.addStretch(); average=QLabel(); average.setStyleSheet("font-size:24pt;font-weight:750;color:#8B2CF5;"); average_layout.addWidget(average); root.addWidget(average_box)
    def color(score): return "#18D647" if score>=8 else "#FFC400" if score>=5 else "#FF4B45"
    def refresh():
        for name,slider in editors.items(): values[name].setText(f"{slider.value()}/10"); values[name].setStyleSheet(f"font-size:12pt;font-weight:700;color:{color(slider.value())};")
        score=sum(slider.value() for slider in editors.values())/len(editors); average.setText(f"{score:.1f}"); average.setStyleSheet(f"font-size:24pt;font-weight:750;color:{color(score)};")
    for slider in editors.values(): slider.valueChanged.connect(refresh)
    refresh()
    hours_row = QWidget()
    hours_layout = QHBoxLayout(hours_row)
    hours_layout.setContentsMargins(0, 2, 0, 2)
    hours_icon = QLabel(); hours_icon.setFixedSize(28, 28)
    hours_icon.setPixmap(IconRegistry.pixmap("clock", 22, variant="dark", category="ui"))
    hours_layout.addWidget(hours_icon)
    hours_label = {
        "Игры": "Общее время в игре",
        "Фильмы": "Общее время просмотра",
        "Сериалы": "Общее время просмотра",
        "Программы": "Общее время использования",
    }.get(media_type, "Общее время")
    label = QLabel(hours_label); label.setMinimumWidth(210); label.setStyleSheet("font-size:11pt;font-weight:550;")
    hours_layout.addWidget(label)
    hours = QDoubleSpinBox(); hours.setRange(0.0, 1000000.0); hours.setDecimals(1); hours.setSingleStep(0.5)
    hours.setValue(float(current_hours or 0.0)); hours.setSuffix(" ч"); hours.setMinimumWidth(180)
    hours.setToolTip("Укажите суммарное время. Velora сама рассчитает изменение.")
    hours_layout.addWidget(hours, 1)
    root.addWidget(hours_row)
    actions=QHBoxLayout(); actions.addStretch(); cancel=QPushButton("ОТМЕНА"); cancel.clicked.connect(dialog.reject); save=QPushButton("СОХРАНИТЬ ОЦЕНКУ"); save.setProperty("primary", True); save.setIcon(IconRegistry.icon("save")); save.clicked.connect(dialog.accept); actions.addWidget(cancel); actions.addWidget(save); root.addLayout(actions)
    if dialog.exec()!=QDialog.DialogCode.Accepted:return None
    return ({name:slider.value() for name,slider in editors.items()}, hours.value())
