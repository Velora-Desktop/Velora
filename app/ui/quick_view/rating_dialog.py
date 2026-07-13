from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget


CRITERIA = (
    ("Графика", "graphics.svg"), ("Саундтрек", "soundtrack.svg"),
    ("Сюжет", "story.svg"), ("Геймплей", "gameplay.svg"),
    ("Атмосфера", "atmosphere.svg"),
)


def request_rating(current: dict[str, int], parent=None) -> dict[str, int] | None:
    dialog=QDialog(parent); dialog.setWindowTitle("Моя оценка"); dialog.setMinimumWidth(640)
    dialog.setStyleSheet("QDialog{background:#070D12;} QLabel{color:#E9EDF1;} QPushButton{min-height:36px;}")
    root=QVBoxLayout(dialog); root.setContentsMargins(22,18,22,18); root.setSpacing(12)
    title=QLabel("ОЦЕНИТЕ ИГРУ"); title.setStyleSheet("font-size:17pt;font-weight:700;"); root.addWidget(title)
    hint=QLabel("Перемещайте ползунки от 1 до 10. Средняя оценка рассчитывается сразу."); hint.setObjectName("muted"); root.addWidget(hint)
    editors={}; values={}; icon_root=Path(__file__).resolve().parents[3]/"assets"/"icons"/"rating"
    for name,icon_name in CRITERIA:
        row=QWidget(); layout=QHBoxLayout(row); layout.setContentsMargins(0,4,0,4); layout.setSpacing(12)
        icon=QLabel(); icon.setFixedSize(28,28); icon.setPixmap(QIcon(str(icon_root/icon_name)).pixmap(22,22)); layout.addWidget(icon)
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
    refresh(); actions=QHBoxLayout(); actions.addStretch(); cancel=QPushButton("ОТМЕНА"); cancel.clicked.connect(dialog.reject); save=QPushButton("СОХРАНИТЬ ОЦЕНКУ"); save.setStyleSheet("background:#6E1BC4;border:1px solid #A54BFF;font-weight:650;"); save.clicked.connect(dialog.accept); actions.addWidget(cancel); actions.addWidget(save); root.addLayout(actions)
    if dialog.exec()!=QDialog.DialogCode.Accepted:return None
    return {name:slider.value() for name,slider in editors.items()}
