from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget


class VeloraSplash(QWidget):
    finished = Signal()
    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(520,300); self.setStyleSheet("background:#020509;border:1px solid #202A33;border-radius:12px;")
        layout=QVBoxLayout(self); self.logo=QLabel("V"); self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter); self.logo.setStyleSheet("font-family:Georgia;font-size:92pt;font-weight:700;color:#D8B5FF;"); layout.addWidget(self.logo)
        caption=QLabel("VELORA"); caption.setAlignment(Qt.AlignmentFlag.AlignCenter); caption.setStyleSheet("font-family:Georgia;font-size:16pt;letter-spacing:6px;color:#EAE4F0;"); layout.addWidget(caption)
        effect=QGraphicsOpacityEffect(self.logo); self.logo.setGraphicsEffect(effect)
        self.animation=QPropertyAnimation(effect,b"opacity",self); self.animation.setDuration(1500); self.animation.setStartValue(0.1); self.animation.setKeyValueAt(0.55,1.0); self.animation.setEndValue(0.25); self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic); self.animation.finished.connect(self.finished)
    def start(self) -> None:
        screen=self.screen().availableGeometry(); self.move(screen.center()-self.rect().center()); self.show(); self.animation.start()
