from __future__ import annotations

from collections import defaultdict
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from app.data.catalog_repository import catalog_categories, load_catalog_items, media_groups
from app.models.game import MEDIA_STATUSES, GameData
from app.services.age_filter_service import AgeFilterService
from app.core.icon_registry import IconRegistry
from app.ui.catalog.game_row import COLUMN_AREA_WIDTH, COLUMN_LABELS, COLUMN_SPACING, COLUMN_WIDTHS, GameRow


class CatalogView(QWidget):
    game_selected = Signal(object)
    placeholder_requested = Signal()
    status_changed = Signal(object, str)
    rating_requested = Signal(object)
    media_changed = Signal(str)
    favorite_changed = Signal(object, bool)
    detail_requested = Signal(object)
    hidden_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.items = load_catalog_items()
        self.rows: list[GameRow] = []
        self.current_media_type = "Игры"
        self.current_category = ""
        self.hide_adult_content = False
        self.page_size = 10
        self.current_page = 1
        self.collapsed_groups: set[str] = set()
        self.group_rows: dict[str, list[GameRow]] = {}
        self.row_groups: dict[GameRow, str] = {}
        self.group_labels: dict[str, QWidget] = {}
        self.group_count_labels: dict[str, QLabel] = {}
        self.sort_directions: dict[str, bool] = {}
        self.header_column_widgets: dict[QWidget, dict[str, QPushButton]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 8)
        root.setSpacing(6)
        controls = QGridLayout()
        self.controls_layout = controls
        controls.setHorizontalSpacing(16)
        specs = (
            ("СОРТИРОВКА:", ("По моей оценке", "По общей оценке", "По названию", "По году выхода", "По автору")),
            ("ФИЛЬТРЫ:", ("Все объекты", "Только избранное", "С моей оценкой", "Без моей оценки")),
            ("ПЛАТФОРМА:", ("Все платформы", "PC", "PlayStation", "Xbox", "Windows", "Web", "Android", "iOS", "iPhone")),
            ("СТАТУС:", ("Все статусы",) + MEDIA_STATUSES["Игры"]),
        )
        self.control_combos: list[QComboBox] = []
        self.control_labels: list[QLabel] = []
        for column, (caption, values) in enumerate(specs):
            label = QLabel(caption)
            label.setObjectName("caption")
            controls.addWidget(label, 0, column)
            self.control_labels.append(label)
            combo = QComboBox()
            combo.addItems(values)
            combo.setMinimumSize(170, 40)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            combo.currentTextChanged.connect(self._controls_changed)
            controls.addWidget(combo, 1, column)
            self.control_combos.append(combo)
        controls.setColumnStretch(4, 1)
        self.search = QLineEdit()
        self.search.setMinimumSize(220, 40)
        self.search.addAction(
            IconRegistry.icon("search"),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.search.textChanged.connect(self._filter)
        controls.addWidget(self.search, 1, 5)
        settings = QPushButton()
        self.settings_button = settings
        settings.setIcon(IconRegistry.icon("settings_gears", variant="dark", category="ui"))
        settings.setToolTip("Настройки каталога")
        settings.setFixedSize(40, 40)
        settings.clicked.connect(self.placeholder_requested)
        controls.addWidget(settings, 1, 6)
        root.addLayout(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content = QWidget()
        self.list_layout = QVBoxLayout(self.content)
        self.list_layout.setContentsMargins(0, 4, 0, 4)
        self.list_layout.setSpacing(0)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

        pagination = QHBoxLayout()
        self.range_label = QLabel()
        pagination.addWidget(self.range_label)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(("10 на странице", "25 на странице", "50 на странице", "100 на странице"))
        self.page_size_combo.setFixedWidth(220)
        self.page_size_combo.currentIndexChanged.connect(self._change_page_size)
        pagination.addWidget(self.page_size_combo)
        pagination.addStretch()
        self.previous_button = QPushButton("‹")
        self.previous_button.clicked.connect(self._previous_page)
        pagination.addWidget(self.previous_button)
        self.page_label = QLabel()
        self.page_label.setMinimumWidth(95)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination.addWidget(self.page_label)
        self.next_button = QPushButton("›")
        self.next_button.clicked.connect(self._next_page)
        pagination.addWidget(self.next_button)
        root.addLayout(pagination)
        self.set_media_type("Игры")
        self._controls_compact = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        compact = event.size().width() < 1320
        if compact != self._controls_compact:
            self._controls_compact = compact
            self._arrange_controls(compact)

    def _arrange_controls(self, compact: bool) -> None:
        for widget in (*self.control_labels, *self.control_combos, self.search):
            self.controls_layout.removeWidget(widget)
        settings_widget = self.settings_button
        self.controls_layout.removeWidget(settings_widget)
        if compact:
            for index, (label, combo) in enumerate(zip(self.control_labels, self.control_combos)):
                row, column = divmod(index, 2)
                self.controls_layout.addWidget(label, row * 2, column)
                self.controls_layout.addWidget(combo, row * 2 + 1, column)
            self.controls_layout.addWidget(self.search, 4, 0, 1, 2)
            if settings_widget:
                self.controls_layout.addWidget(settings_widget, 4, 2)
            self.controls_layout.setColumnStretch(0, 1); self.controls_layout.setColumnStretch(1, 1)
        else:
            for index, (label, combo) in enumerate(zip(self.control_labels, self.control_combos)):
                self.controls_layout.addWidget(label, 0, index)
                self.controls_layout.addWidget(combo, 1, index)
            self.controls_layout.addWidget(self.search, 1, 5)
            if settings_widget:
                self.controls_layout.addWidget(settings_widget, 1, 6)

    def categories_for(self, media_type: str) -> dict[str, int]:
        return catalog_categories(self.items, media_type)

    @classmethod
    def category_counts(cls) -> dict[str, int]:
        return catalog_categories(load_catalog_items(), "Игры")

    def set_media_type(self, media_type: str, category: str = "") -> None:
        self.current_media_type = media_type
        categories = self.categories_for(media_type)
        wanted = category.upper()
        self.current_category = wanted if wanted in categories else next(iter(categories), "")
        self.current_page = 1
        self.search.clear()
        self._configure_controls()
        self._rebuild()
        self.media_changed.emit(media_type)

    def set_category(self, category: str) -> None:
        category = category.upper()
        if category != self.current_category:
            self.current_category = category
            self.current_page = 1
            self._rebuild()

    def _configure_controls(self) -> None:
        sorting = self.control_combos[0]
        sorting.blockSignals(True)
        current_sort = sorting.currentData() or "personal"
        sorting.clear()
        creator_label = {
            "Игры": "разработчику",
            "Фильмы": "режиссёру",
            "Сериалы": "создателю",
            "Программы": "разработчику",
        }.get(self.current_media_type, "автору")
        for text, key in (
            ("По моей оценке", "personal"),
            ("По общей оценке", "general"),
            ("По названию", "title"),
            ("По году выхода", "year"),
            (f"По {creator_label}", "developer"),
        ):
            sorting.addItem(text, key)
        selected_index = max(0, sorting.findData(current_sort))
        sorting.setCurrentIndex(selected_index)
        sorting.blockSignals(False)
        status = self.control_combos[3]
        status.blockSignals(True)
        status.clear()
        status.addItem("Все статусы")
        status.addItems(MEDIA_STATUSES.get(self.current_media_type, ()))
        status.blockSignals(False)
        platform = self.control_combos[2]
        platform.blockSignals(True); platform.clear()
        watch_mode = self.current_media_type in ("Фильмы", "Сериалы")
        platform.addItem("Все сервисы" if watch_mode else "Все платформы")
        tokens = sorted({token.strip() for item in self.items if item.media_type == self.current_media_type for token in item.platform.split(";") if token.strip()})
        platform.addItems(tokens); platform.blockSignals(False)
        self.control_labels[2].setText("ГДЕ СМОТРЕТЬ:" if watch_mode else "ПЛАТФОРМА:")
        self.search.setPlaceholderText(f"Поиск: {self.current_media_type.lower()}...")

    def _clear_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _rebuild(self) -> None:
        self._clear_list()
        self.rows.clear()
        self.group_rows.clear()
        self.row_groups.clear()
        self.group_labels.clear()
        self.group_count_labels.clear()
        self.header_column_widgets.clear()
        groups = media_groups(self.items, self.current_media_type, self.current_category)
        for group_name, games in groups.items():
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 5, 8, 5)
            header_layout.setSpacing(COLUMN_SPACING)
            toggle = QPushButton("\u2212" if group_name not in self.collapsed_groups else "+")
            toggle.setObjectName("groupToggle")
            toggle.setFixedSize(28, 28)
            toggle.setToolTip("Скрыть группу" if group_name not in self.collapsed_groups else "Показать группу")
            toggle.clicked.connect(lambda checked=False, name=group_name: self._toggle_group(name))
            header_layout.addWidget(toggle)
            count = QLabel(f"{group_name.upper()} ({len(games)})")
            header_layout.addWidget(count)
            header_layout.addStretch()
            header_columns, header_widgets = self._column_header_widget()
            header_layout.addWidget(header_columns)
            self.list_layout.addWidget(header)
            self.group_labels[group_name] = header
            self.header_column_widgets[header] = header_widgets
            self.group_count_labels[group_name] = count
            rows = []
            for game in games:
                row = GameRow(game)
                row.selected.connect(self._select)
                row.placeholder_requested.connect(self.placeholder_requested)
                row.status_changed.connect(self.status_changed)
                row.rating_requested.connect(self.rating_requested)
                row.favorite_changed.connect(self.favorite_changed)
                row.detail_requested.connect(self.detail_requested)
                row.hidden_requested.connect(self.hidden_requested)
                self.list_layout.addWidget(row)
                self.rows.append(row)
                rows.append(row)
                self.row_groups[row] = group_name
            self.group_rows[group_name] = rows
        selected_sort = self.control_combos[0].currentData() or "personal"
        for rows in self.group_rows.values():
            rows.sort(
                key=lambda row: self._sort_value(row, selected_sort),
                reverse=selected_sort in ("general", "personal", "year", "age"),
            )
        self._reorder_visual_rows()
        self.list_layout.addStretch()
        self._apply_view()
        # A previous horizontal position must not leak into another media
        # section and visually detach headers from the title column.
        QTimer.singleShot(0, lambda: self.scroll.horizontalScrollBar().setValue(0))

    def _column_header_widget(self) -> tuple[QWidget, dict[str, QPushButton]]:
        container = QWidget()
        container.setFixedWidth(COLUMN_AREA_WIDTH)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(COLUMN_SPACING)
        widgets: dict[str, QPushButton] = {}
        for text, key in self._column_headers():
            button = QPushButton(text)
            button.setFixedWidth(COLUMN_WIDTHS[key])
            button.setFlat(True)
            button.clicked.connect(lambda checked=False, column=key: self._sort_by_column(column))
            layout.addWidget(button)
            widgets[key] = button
        more_placeholder = QWidget()
        more_placeholder.setFixedWidth(COLUMN_WIDTHS["more"])
        layout.addWidget(more_placeholder)
        return container, widgets

    def _column_headers(self) -> tuple[tuple[str, str], ...]:
        creator = {"Игры": "Разработчик", "Фильмы": "Режиссёр", "Сериалы": "Создатель", "Программы": "Разработчик"}[self.current_media_type]
        platform = "Где смотреть" if self.current_media_type in ("Фильмы", "Сериалы") else "Платформа"
        mode = {"Игры": "Кол-во игроков", "Фильмы": "Длительность", "Сериалы": "Сезоны", "Программы": "Тип"}[self.current_media_type]
        return ((COLUMN_LABELS["general"], "general"), (COLUMN_LABELS["personal"], "personal"), (COLUMN_LABELS["status"], "status"),
                (creator, "developer"), ("Год выхода", "year"), (platform, "platform"),
                (mode, "mode"), ("Возраст", "age"))

    def _toggle_group(self, name: str) -> None:
        if name in self.collapsed_groups:
            self.collapsed_groups.remove(name)
        else:
            self.collapsed_groups.add(name)
        header = self.group_labels.get(name)
        if header is not None:
            toggle = header.findChild(QPushButton, "groupToggle")
            if toggle is not None:
                collapsed = name in self.collapsed_groups
                toggle.setText("+" if collapsed else "\u2212")
                toggle.setToolTip("Показать группу" if collapsed else "Скрыть группу")
        self._apply_view()

    def _sort_by_column(self, column: str) -> None:
        reverse = self.sort_directions.get(column, column in ("general", "personal", "year", "age"))
        self.sort_directions[column] = not reverse
        for rows in self.group_rows.values():
            rows.sort(key=lambda row: self._sort_value(row, column), reverse=reverse)
        self._reorder_visual_rows()
        self._apply_view()

    def _reorder_visual_rows(self) -> None:
        for name, rows in self.group_rows.items():
            self.list_layout.removeWidget(self.group_labels[name])
            for row in rows: self.list_layout.removeWidget(row)
        index = 0
        for name, rows in self.group_rows.items():
            self.list_layout.insertWidget(index, self.group_labels[name]); index += 1
            for row in rows: self.list_layout.insertWidget(index, row); index += 1

    @staticmethod
    def _score(value: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return -1.0

    def _filter(self, _text: str) -> None:
        self.current_page = 1
        self._apply_view()

    def _controls_changed(self, _text: str) -> None:
        self.current_page = 1
        column = self.control_combos[0].currentData()
        if column:
            reverse = column in ("general", "personal", "year", "age")
            for rows in self.group_rows.values():
                rows.sort(key=lambda row: self._sort_value(row, column), reverse=reverse)
            self._reorder_visual_rows()
        self._apply_view()

    def _matching_rows(self) -> list[GameRow]:
        query = self.search.text().strip().casefold()
        filter_mode = self.control_combos[1].currentText()
        platform = self.control_combos[2].currentText()
        status = self.control_combos[3].currentText()
        rows = []
        for row in self.rows:
            game = row.game
            if query and query not in game.title.casefold():
                continue
            if self.hide_adult_content and not AgeFilterService.is_visible(game, True):
                continue
            if game.hidden:
                continue
            if filter_mode == "Только избранное" and not game.favorite:
                continue
            if filter_mode == "С моей оценкой" and game.personal_score == "—":
                continue
            if filter_mode == "Без моей оценки" and game.personal_score != "—":
                continue
            if platform not in ("Все платформы", "Все сервисы") and platform.casefold() not in game.platform.casefold():
                continue
            if status != "Все статусы" and game.status != status:
                continue
            rows.append(row)
        sort_column = self.control_combos[0].currentData() or "personal"
        rows.sort(
            key=lambda row: self._sort_value(row, sort_column),
            reverse=sort_column in ("general", "personal", "year", "age"),
        )
        return rows

    def _sort_value(self, row: GameRow, column: str):
        game = row.game
        if column == "general": return self._score(game.general_score)
        if column == "personal": return self._score(game.personal_score)
        if column == "status":
            statuses = MEDIA_STATUSES.get(game.media_type, ())
            return statuses.index(game.status) if game.status in statuses else len(statuses)
        if column == "developer": return (game.developer or "").casefold()
        if column == "year":
            try: return int(game.year or 0)
            except (TypeError, ValueError): return 0
        if column == "platform": return (game.platform or "").casefold()
        if column == "mode": return (game.mode or "").casefold()
        if column == "age": return int(game.age_rating or 0)
        return (game.title or "").casefold()

    def _apply_view(self) -> None:
        matching = self._matching_rows()
        total = len(matching)
        pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, pages)
        start = (self.current_page - 1) * self.page_size
        end = min(start + self.page_size, total)
        visible = set(matching[start:end])
        for name, label in self.group_count_labels.items():
            label.setText(f"{name.upper()} ({sum(row in matching for row in self.group_rows[name])})")
        for row in self.rows:
            row.setVisible(row in visible and self.row_groups[row] not in self.collapsed_groups)
        for name, header in self.group_labels.items():
            header.setVisible(any(row in visible for row in self.group_rows[name]))
        self.range_label.setText(f"ПОКАЗАНО: {start + 1 if total else 0}–{end} ИЗ {total}")
        self.page_label.setText(f"{self.current_page} из {pages}")
        self.previous_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < pages)

    def _select(self, game: GameData) -> None:
        for row in self.rows:
            row.set_selected(row.game is game)
        self.game_selected.emit(game)

    def select_game(self, game: GameData) -> None:
        if game.media_type != self.current_media_type or game.category.upper() != self.current_category:
            self.set_media_type(game.media_type, game.category)
        self._select(game)

    def set_game_status(self, game: GameData, status: str) -> None:
        game.status = status
        for row in self.rows:
            if row.game is game:
                row.set_status(status, False)
                break

    def set_game_score(self, game: GameData, score: str) -> None:
        game.personal_score = score
        for row in self.rows:
            if row.game is game:
                row.set_personal_score(score)
                break
        self._apply_view()

    def refresh_filters(self, *_args) -> None:
        self._apply_view()

    def set_hide_adult_content(self, enabled: bool) -> None:
        self.hide_adult_content = enabled
        self.current_page = 1
        self._apply_view()

    def _change_page_size(self, index: int) -> None:
        self.page_size = (10, 25, 50, 100)[index]
        self.current_page = 1
        self._apply_view()

    def _previous_page(self) -> None:
        self.current_page = max(1, self.current_page - 1)
        self._apply_view()

    def _next_page(self) -> None:
        self.current_page += 1
        self._apply_view()
