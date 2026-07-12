from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget, QHBoxLayout

from app.ui.catalog.game_row import GameData, GameRow


class CatalogView(QWidget):
    game_selected = Signal(object)
    placeholder_requested = Signal()

    GROUPS = {
        "ОТ ПЕРВОГО ЛИЦА · 5": (
            GameData("Call of Duty", "8.7", "8.5", "ПРОХОЖУ", "Infinity Ward", "2003", "PC", "Одиночная", "15 ч"),
            GameData("Doom Eternal", "9.0", "—", "НЕ НАЧИНАЛ", "id Software", "2020", "PC", "Одиночная"),
            GameData("Half-Life 2", "9.4", "9.2", "ПРОШЁЛ", "Valve", "2004", "PC", "Одиночная", "18 ч"),
            GameData("Battlefield 1", "8.4", "7.8", "ПРОШЁЛ", "DICE", "2016", "PC", "Сетевая", "42 ч"),
            GameData("Metro Exodus", "8.6", "—", "НЕ НАЧИНАЛ", "4A Games", "2019", "PC", "Одиночная"),
        ),
        "ОТ ТРЕТЬЕГО ЛИЦА · 2": (
            GameData("Max Payne 3", "8.5", "8.9", "ПРОШЁЛ", "Rockstar", "2012", "PC", "Одиночная", "13 ч"),
            GameData("Resident Evil 4", "9.2", "—", "ПРОХОЖУ", "Capcom", "2023", "PC", "Одиночная", "6 ч"),
        ),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.rows: list[GameRow] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 8)
        header = QHBoxLayout()
        title = QLabel("Шутеры · 7")
        title.setStyleSheet("font-size:20px; font-weight:600;")
        header.addWidget(title)
        header.addStretch()
        search = QLineEdit()
        search.setPlaceholderText("Поиск...")
        search.setMaximumWidth(300)
        search.textChanged.connect(self._filter)
        header.addWidget(search)
        root.addLayout(header)
        controls = QHBoxLayout()
        for text in ("Сортировка", "Фильтры", "Платформа", "Статус"):
            button = QPushButton(text)
            button.clicked.connect(self.placeholder_requested)
            controls.addWidget(button)
        controls.addStretch()
        root.addLayout(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.list_layout = QVBoxLayout(content)
        self.list_layout.setContentsMargins(0, 4, 0, 4)
        for group_name, games in self.GROUPS.items():
            label = QLabel(group_name)
            label.setObjectName("groupHeader")
            self.list_layout.addWidget(label)
            for game in games:
                row = GameRow(game)
                row.selected.connect(self._select)
                row.placeholder_requested.connect(self.placeholder_requested)
                self.rows.append(row)
                self.list_layout.addWidget(row)
        self.list_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        pagination = QHBoxLayout()
        pagination.addStretch()
        pagination.addWidget(QLabel("‹   1   2   3   …   43   ›      Показывать: 10"))
        pagination.addStretch()
        root.addLayout(pagination)

    def _select(self, game: GameData) -> None:
        for row in self.rows:
            row.set_selected(row.game == game)
        self.game_selected.emit(game)

    def _filter(self, text: str) -> None:
        query = text.strip().casefold()
        for row in self.rows:
            row.setVisible(not query or query in row.game.title.casefold())

