from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QTabWidget, QVBoxLayout, QWidget


class SettingsDialog(QDialog):
    adult_filter_changed = Signal(bool)
    hidden_restored = Signal(object)

    def __init__(self, hide_adult_content: bool, games=(), parent=None) -> None:
        super().__init__(parent); self.games=list(games); self.setWindowTitle("Настройки Velora"); self.setMinimumSize(680,520)
        root=QVBoxLayout(self); title=QLabel("НАСТРОЙКИ"); title.setStyleSheet("font-size:18pt;font-weight:600;"); root.addWidget(title)
        tabs=QTabWidget(); root.addWidget(tabs,1)
        general=QWidget(); gl=QVBoxLayout(general); gl.addWidget(QLabel("ОБЩЕЕ")); gl.addWidget(QLabel("Локальные настройки интерфейса Velora.")); gl.addStretch(); tabs.addTab(general,"ОБЩЕЕ")
        content=QWidget(); cl=QVBoxLayout(content)
        self.adult_filter=QCheckBox("Скрывать карточки 18+"); self.adult_filter.setChecked(hide_adult_content); self.adult_filter.toggled.connect(self.adult_filter_changed); cl.addWidget(self.adult_filter)
        cl.addWidget(QLabel("СКРЫТЫЕ ОБЪЕКТЫ · ИГРЫ / ФИЛЬМЫ / СЕРИАЛЫ"))
        self.hidden=QListWidget(); self._refresh(); cl.addWidget(self.hidden,1)
        row=QHBoxLayout(); row.addStretch(); restore=QPushButton("ВЕРНУТЬ В КАТАЛОГ"); restore.clicked.connect(self._restore); row.addWidget(restore); cl.addLayout(row); tabs.addTab(content,"КОНТЕНТ")

    def _refresh(self):
        self.hidden.clear()
        for game in self.games:
            if game.hidden:
                self.hidden.addItem(f"{game.media_type}  /  {game.title}"); self.hidden.item(self.hidden.count()-1).setData(256,game)

    def _restore(self):
        item=self.hidden.currentItem()
        if item is None:return
        game=item.data(256); game.hidden=False; self.hidden_restored.emit(game); self._refresh()
