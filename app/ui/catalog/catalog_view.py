from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget, QHBoxLayout

from app.models.game import GameData
from app.ui.catalog.game_row import COLUMN_WIDTHS, GameRow


class CatalogView(QWidget):
    game_selected = Signal(object)
    placeholder_requested = Signal()
    status_changed = Signal(object, str)

    GROUPS = {
        "ОТ ПЕРВОГО ЛИЦА": (
            GameData("CALL OF DUTY", "9.1", "—", "НЕ НАЧИНАЛ", "Infinity Ward", "2003", "PC/PS3/X360", "1P/MULTI", publisher="Activision", age_rating=16, catalog_id="g-shooter-fps-001", subgroup="От первого лица", critic_scores={"Metacritic": 9.1, "IGN": None, "DualShockers": None, "PC Gamer": None}),
            GameData("DOOM ETERNAL", "9.2", "—", "НЕ НАЧИНАЛ", "id Software", "2020", "PC/PS4/XONE", "1P/MULTI", age_rating=18, catalog_id="g-shooter-fps-002", subgroup="От первого лица", critic_scores={"Metacritic": 8.9, "IGN": 9.5, "DualShockers": 9.0, "PC Gamer": 9.4}),
            GameData("HALF-LIFE 2", "9", "—", "НЕ НАЧИНАЛ", "Valve", "2004", "PC", "1P", age_rating=16),
            GameData("BORDERLANDS 2", "8", "—", "НЕ НАЧИНАЛ", "Gearbox Software", "2012", "PC/PS3/X360", "1P/CO-OP", age_rating=18),
            GameData("MEDAL OF HONOR", "7", "—", "НЕ НАЧИНАЛ", "EA DICE", "2010", "PC/PS3/X360", "1P/MULTI", age_rating=16),
        ),
        "ОТ ТРЕТЬЕГО ЛИЦА": (
            GameData("MAX PAYNE 3", "5", "—", "НЕ НАЧИНАЛ", "Rockstar Studios", "2012", "PC/PS3/X360", "1P", age_rating=18),
            GameData("RESIDENT EVIL 4", "9", "—", "НЕ НАЧИНАЛ", "Capcom", "2005", "PC/PS2/PS3", "1P", age_rating=18),
        ),
    }

    @classmethod
    def category_counts(cls) -> dict[str, int]:
        """Return counts derived from the cards currently loaded in the catalog."""
        from app.data.catalog_repository import load_game_groups
        groups = load_game_groups() or cls.GROUPS
        return {"ШУТЕРЫ": sum(len(games) for games in groups.values())}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from app.data.catalog_repository import load_game_groups
        self.catalog_groups = load_game_groups() or self.GROUPS
        self.rows: list[GameRow] = []
        self.row_groups: dict[GameRow, str] = {}
        self.group_labels: dict[str, QWidget] = {}
        self.search_query = ""
        self.current_page = 1
        self.page_size = 10
        self.sort_mode = "По моей оценке"
        self.filter_mode = "Все игры"
        self.platform_mode = "Все платформы"
        self.status_mode = "Все статусы"
        self.current_category = "ШУТЕРЫ"
        self.hide_adult_content = False
        self.collapsed_groups: set[str] = set()
        self.group_sort: dict[str, tuple[str, bool]] = {}
        self.group_sort_buttons: dict[tuple[str, str], QPushButton] = {}
        self.collapse_buttons: dict[str, QPushButton] = {}
        self.group_count_labels: dict[str, QLabel] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 8)
        root.setSpacing(6)
        controls = QGridLayout()
        controls.setHorizontalSpacing(16)
        controls.setVerticalSpacing(5)
        control_specs = (
            ("СОРТИРОВКА:", ("По моей оценке", "По общей оценке", "По названию", "По году выхода", "По разработчику")),
            ("ФИЛЬТРЫ:", ("Все игры", "Только избранное", "С моей оценкой", "Без моей оценки")),
            ("ПЛАТФОРМА:", ("Все платформы", "PC", "PlayStation", "Xbox")),
            ("СТАТУС:", ("Все статусы", "НЕ НАЧИНАЛ", "ПРОХОЖУ", "ПРОШЁЛ", "БРОСИЛ")),
        )
        self.control_combos: list[QComboBox] = []
        for column, (caption, values) in enumerate(control_specs):
            label = QLabel(caption)
            label.setObjectName("caption")
            controls.addWidget(label, 0, column)
            combo = QComboBox()
            combo.addItems(values)
            combo.setFixedSize(245, 40)
            combo.currentTextChanged.connect(self._controls_changed)
            self.control_combos.append(combo)
            controls.addWidget(combo, 1, column)
        controls.setColumnStretch(4, 1)
        search = QLineEdit()
        search.setPlaceholderText("Поиск по играм...")
        search.setFixedSize(285, 40)
        search_icon = Path(__file__).resolve().parents[3] / "assets" / "icons" / "search.svg"
        search.addAction(QIcon(str(search_icon)), QLineEdit.ActionPosition.TrailingPosition)
        search.textChanged.connect(self._filter)
        controls.addWidget(search, 1, 5)
        settings = QPushButton("⚙")
        settings.setFixedSize(40, 40)
        settings.setStyleSheet("font-family:'Segoe UI Symbol'; font-size:17px; color:#D8DDE3; border:1px solid #27333D; border-radius:6px; background:#091118;")
        settings.clicked.connect(self.placeholder_requested)
        controls.addWidget(settings, 1, 6)
        root.addLayout(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.list_layout = QVBoxLayout(content)
        self.list_layout.setContentsMargins(0, 4, 0, 4)
        self.list_layout.setSpacing(0)
        self.group_rows: dict[str, list[GameRow]] = {}
        for group_name, games in self.catalog_groups.items():
            group_header = self._build_group_header(group_name, len(games))
            self.group_labels[group_name] = group_header
            self.list_layout.addWidget(group_header)
            self.group_rows[group_name] = []
            for game in games:
                row = GameRow(game)
                row.selected.connect(self._select)
                row.placeholder_requested.connect(self.placeholder_requested)
                row.status_changed.connect(self.status_changed)
                row.favorite_changed.connect(lambda game, selected: self._apply_view())
                self.rows.append(row)
                self.row_groups[row] = group_name
                self.group_rows[group_name].append(row)
                self.list_layout.addWidget(row)
        self.list_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        pagination = QHBoxLayout()
        self.range_label = QLabel()
        self.range_label.setObjectName("muted")
        pagination.addWidget(self.range_label)
        pagination.addSpacing(18)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(("10 на странице", "25 на странице", "50 на странице", "100 на странице"))
        self.page_size_combo.setFixedWidth(290)
        self.page_size_combo.currentIndexChanged.connect(self._change_page_size)
        pagination.addWidget(self.page_size_combo)
        pagination.addStretch()
        self.previous_button = QPushButton("‹")
        self.previous_button.setFixedSize(34, 32)
        self.previous_button.clicked.connect(self._previous_page)
        pagination.addWidget(self.previous_button)
        self.page_label = QLabel()
        self.page_label.setMinimumWidth(95)
        self.page_label.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        pagination.addWidget(self.page_label)
        self.next_button = QPushButton("›")
        self.next_button.setFixedSize(34, 32)
        self.next_button.clicked.connect(self._next_page)
        pagination.addWidget(self.next_button)
        root.addLayout(pagination)
        self._apply_view()

    def _build_group_header(self, group_name: str, count: int) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 8, 8, 5)
        layout.setSpacing(8)
        collapse = QPushButton("−")
        collapse.setFixedSize(24, 24)
        collapse.setToolTip("Свернуть группу")
        collapse.setStyleSheet("font-size:14pt; padding:0; border:0; background:transparent; text-align:center;")
        collapse.clicked.connect(lambda checked=False, name=group_name: self._toggle_group(name))
        self.collapse_buttons[group_name] = collapse
        layout.addWidget(collapse)
        group_label = QLabel(f"{group_name} ({count})")
        group_label.setObjectName("groupHeader")
        self.group_count_labels[group_name] = group_label
        layout.addWidget(group_label, 2)
        columns = (
            ("Общая оценка", "general", COLUMN_WIDTHS["general"]),
            ("Моя оценка", "personal", COLUMN_WIDTHS["personal"]),
            ("Статус", "status", COLUMN_WIDTHS["status"]),
            ("Разработчик", "developer", COLUMN_WIDTHS["developer"]),
            ("Год выхода", "year", COLUMN_WIDTHS["year"]),
            ("Платформа", "platform", COLUMN_WIDTHS["platform"]),
            ("Кол-во игроков", "mode", COLUMN_WIDTHS["mode"]),
            ("Возраст", "age", COLUMN_WIDTHS["age"]),
        )
        for column_index, (text, key, width) in enumerate(columns):
            button = QPushButton(text)
            button.setFixedWidth(width)
            button.setToolTip("Сортировать эту группу")
            button.setStyleSheet(
                "QPushButton { font-family:'Segoe UI'; font-size:9pt; color:#9CA7B1; "
                "background:transparent; border:0; padding:2px 4px; }"
                "QPushButton:hover { color:white; background:#111A22; border-radius:4px; }"
            )
            if column_index in (0, 1, 2):
                button.setStyleSheet(button.styleSheet() + "QPushButton { text-align:center; }")
            else:
                button.setStyleSheet(button.styleSheet() + "QPushButton { text-align:left; }")
            button.clicked.connect(lambda checked=False, name=group_name, field=key: self._sort_group(name, field))
            self.group_sort_buttons[(group_name, key)] = button
            layout.addWidget(button)
        trailing = QWidget()
        trailing.setFixedWidth(COLUMN_WIDTHS["more"])
        layout.addWidget(trailing)
        return header

    def _toggle_group(self, group_name: str) -> None:
        if group_name in self.collapsed_groups:
            self.collapsed_groups.remove(group_name)
            self.collapse_buttons[group_name].setText("−")
            self.collapse_buttons[group_name].setToolTip("Свернуть группу")
        else:
            self.collapsed_groups.add(group_name)
            self.collapse_buttons[group_name].setText("+")
            self.collapse_buttons[group_name].setToolTip("Развернуть группу")
        self._apply_view()

    def _sort_group(self, group_name: str, field: str) -> None:
        previous = self.group_sort.get(group_name)
        ascending = not previous[1] if previous and previous[0] == field else False
        self.group_sort[group_name] = (field, ascending)
        for (name, key), button in self.group_sort_buttons.items():
            base_text = {
                "general": "Общая оценка", "personal": "Моя оценка", "status": "Статус",
                "developer": "Разработчик", "year": "Год выхода", "platform": "Платформа",
                "mode": "Кол-во игроков", "age": "Возраст",
            }[key]
            if name == group_name and key == field:
                button.setText(f"{base_text} {'↑' if ascending else '↓'}")
            elif name == group_name:
                button.setText(base_text)
        self._reorder_rows()

    def _select(self, game: GameData) -> None:
        for row in self.rows:
            row.set_selected(row.game == game)
        self.game_selected.emit(game)

    def select_game(self, game: GameData) -> None:
        self._select(game)

    def set_game_status(self, game: GameData, status: str) -> None:
        for row in self.rows:
            if row.game is game:
                row.set_status(status, record_history=False)
                return

    def set_game_score(self, game: GameData, score: str) -> None:
        for row in self.rows:
            if row.game is game:
                row.set_personal_score(score)
                self._apply_view()
                return

    def refresh_filters(self, game: GameData | None = None, value: bool | None = None) -> None:
        self._apply_view()

    def _filter(self, text: str) -> None:
        self.search_query = text.strip().casefold()
        self.current_page = 1
        self._apply_view()

    def _matching_rows(self) -> list[GameRow]:
        if self.current_category != "ШУТЕРЫ":
            return []
        rows = [row for row in self.rows if not self.search_query or self.search_query in row.game.title.casefold()]
        if self.filter_mode == "Только избранное":
            rows = [row for row in rows if row.game.favorite]
        elif self.filter_mode == "С моей оценкой":
            rows = [row for row in rows if row.game.personal_score != "—"]
        elif self.filter_mode == "Без моей оценки":
            rows = [row for row in rows if row.game.personal_score == "—"]
        if self.platform_mode != "Все платформы":
            aliases = {"PC": ("PC", "WIN"), "PlayStation": ("PS",), "Xbox": ("XBOX", "XONE", "X360")}
            tokens = aliases[self.platform_mode]
            rows = [row for row in rows if any(token in row.game.platform.upper() for token in tokens)]
        if self.status_mode != "Все статусы":
            rows = [row for row in rows if row.game.status == self.status_mode]
        if self.hide_adult_content:
            rows = [row for row in rows if row.game.age_rating < 18]
        rows = [row for row in rows if not row.game.hidden]
        return rows

    def set_hide_adult_content(self, enabled: bool) -> None:
        self.hide_adult_content = enabled
        self.current_page = 1
        self._apply_view()

    def set_category(self, category: str) -> None:
        self.current_category = category
        self.current_page = 1
        self._apply_view()

    def _apply_view(self) -> None:
        matching = self._sorted_rows(self._matching_rows())
        total = len(matching)
        for group_name, label in self.group_count_labels.items():
            group_count = sum(1 for row in matching if self.row_groups[row] == group_name)
            label.setText(f"{group_name} ({group_count})")
        page_count = max(1, (total + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, page_count)
        start = (self.current_page - 1) * self.page_size
        end = min(start + self.page_size, total)
        visible_rows = set(matching[start:end])
        for row in self.rows:
            row.setVisible(row in visible_rows and self.row_groups[row] not in self.collapsed_groups)
        for name, label in self.group_labels.items():
            label.setVisible(any(row in visible_rows and self.row_groups[row] == name for row in self.rows))
        shown_start = start + 1 if total else 0
        self.range_label.setText(f"ПОКАЗАНО: {shown_start}–{end} ИЗ {total}")
        self.page_label.setText(f"{self.current_page} из {page_count}")
        self.previous_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < page_count)
        self._reorder_rows()

    def _controls_changed(self) -> None:
        self.sort_mode, self.filter_mode, self.platform_mode, self.status_mode = (
            combo.currentText() for combo in self.control_combos
        )
        self.current_page = 1
        self._apply_view()

    def _sorted_rows(self, rows: list[GameRow]) -> list[GameRow]:
        def score(value: str) -> float:
            try:
                return float(value)
            except ValueError:
                return -1.0
        if self.sort_mode == "По моей оценке":
            return sorted(rows, key=lambda row: score(row.game.personal_score), reverse=True)
        if self.sort_mode == "По общей оценке":
            return sorted(rows, key=lambda row: score(row.game.general_score), reverse=True)
        if self.sort_mode == "По названию":
            return sorted(rows, key=lambda row: row.game.title.casefold())
        if self.sort_mode == "По году выхода":
            return sorted(rows, key=lambda row: int(row.game.year), reverse=True)
        return sorted(rows, key=lambda row: row.game.developer.casefold())

    def _reorder_rows(self) -> None:
        for group_name, group_rows in self.group_rows.items():
            header = self.group_labels[group_name]
            self.list_layout.removeWidget(header)
            for row in group_rows:
                self.list_layout.removeWidget(row)
        insert_at = 0
        matching_order = self._sorted_rows(self._matching_rows())
        for group_name, group_rows in self.group_rows.items():
            header = self.group_labels[group_name]
            self.list_layout.insertWidget(insert_at, header)
            insert_at += 1
            ordered_group = [row for row in matching_order if row in group_rows]
            if group_name in self.group_sort:
                field, ascending = self.group_sort[group_name]
                ordered_group = self._sort_rows_by_field(ordered_group, field, ascending)
            ordered_group += [row for row in group_rows if row not in ordered_group]
            for row in ordered_group:
                self.list_layout.insertWidget(insert_at, row)
                insert_at += 1

    @staticmethod
    def _sort_rows_by_field(rows: list[GameRow], field: str, ascending: bool) -> list[GameRow]:
        status_order = {"НЕ НАЧИНАЛ": 0, "ПРОХОЖУ": 1, "ПРОШЁЛ": 2, "БРОСИЛ": 3}

        def numeric(value: str) -> float:
            try:
                return float(value)
            except ValueError:
                return -1.0

        key_functions = {
            "general": lambda row: numeric(row.game.general_score),
            "personal": lambda row: numeric(row.game.personal_score),
            "status": lambda row: status_order.get(row.game.status, -1),
            "developer": lambda row: row.game.developer.casefold(),
            "year": lambda row: int(row.game.year),
            "platform": lambda row: row.game.platform.casefold(),
            "mode": lambda row: row.game.mode.casefold(),
            "age": lambda row: row.game.age_rating,
        }
        return sorted(rows, key=key_functions[field], reverse=not ascending)

    def _change_page_size(self, index: int) -> None:
        self.page_size = (10, 25, 50, 100)[index]
        self.current_page = 1
        self._apply_view()

    def _previous_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._apply_view()

    def _next_page(self) -> None:
        page_count = max(1, (len(self._matching_rows()) + self.page_size - 1) // self.page_size)
        if self.current_page < page_count:
            self.current_page += 1
            self._apply_view()
