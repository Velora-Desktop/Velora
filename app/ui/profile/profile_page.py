from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.data.user_repository import LocalProfile, UserRepository
from app.ui.profile.statistics_dashboard import StatisticsDashboard
from app.ui.profile.profile_overview import ProfileOverview
from app.ui.profile.profile_widgets import AvatarLabel, GlowingTabBar, store_profile_avatar
from app.navigation.routes import catalog_uri


class SortableItem(QTableWidgetItem):
    def __lt__(self, other) -> bool:
        try: return float(self.text()) < float(other.text())
        except ValueError: return self.text().casefold() < other.text().casefold()


class ProfilePage(QWidget):
    catalog_item_requested = Signal(str)
    def __init__(self, repository: UserRepository, parent=None) -> None:
        super().__init__(parent); self.repository = repository; self.games = []
        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 22); root.setSpacing(14)
        heading = QHBoxLayout(); title = QLabel("МОЙ VELORA"); title.setStyleSheet("font-family:Georgia; font-size:26pt; letter-spacing:2px;")
        heading.addWidget(title); heading.addStretch(); self.profile_name = QLabel(); self.profile_name.setStyleSheet("font-size:14pt; font-weight:600;"); heading.addWidget(self.profile_name)
        root.addLayout(heading)
        self.tabs = QTabWidget(); self.tabs.setObjectName("profileTabs"); self.tabs.setDocumentMode(True); self.tabs.setTabBar(GlowingTabBar())
        self.tabs.addTab(self._build_overview_tab(), "ОБЗОР")
        self.tabs.addTab(self._build_ratings_tab(), "МОИ ОЦЕНКИ")
        self.tabs.addTab(self._build_favorites_tab(), "ИЗБРАННОЕ")
        self.tabs.addTab(self._build_statistics_tab(), "СТАТИСТИКА")
        self.tabs.addTab(self._build_profile_tab(), "ПРОФИЛЬ")
        root.addWidget(self.tabs, 1)

    def _build_overview_tab(self) -> QWidget:
        self.overview = ProfileOverview()
        self.overview.section_requested.connect(self.tabs.setCurrentIndex)
        self.overview.catalog_item_requested.connect(self.catalog_item_requested.emit)
        return self.overview

    def _build_profile_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(18, 22, 18, 18)
        caption = QLabel("АВАТАР ПРОФИЛЯ"); caption.setObjectName("caption"); layout.addWidget(caption)
        avatar_container = QWidget(); avatar_container.setFixedHeight(140); avatar_row = QHBoxLayout(avatar_container); avatar_row.setContentsMargins(0,0,0,0); avatar_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.avatar_preview = AvatarLabel(124); avatar_row.addWidget(self.avatar_preview,0,Qt.AlignmentFlag.AlignTop)
        avatar_actions = QVBoxLayout(); avatar_actions.setAlignment(Qt.AlignmentFlag.AlignTop); choose_avatar = QPushButton("ВЫБРАТЬ ИЗОБРАЖЕНИЕ"); choose_avatar.clicked.connect(self._choose_avatar); avatar_actions.addWidget(choose_avatar)
        remove_avatar = QPushButton("УБРАТЬ АВАТАР"); remove_avatar.clicked.connect(self._remove_avatar); avatar_actions.addWidget(remove_avatar); avatar_row.addLayout(avatar_actions); avatar_row.addStretch(); layout.addWidget(avatar_container)
        caption = QLabel("ИМЯ ПРОФИЛЯ"); caption.setObjectName("caption"); layout.addWidget(caption)
        row = QHBoxLayout(); self.name_edit = QLineEdit(); self.name_edit.setMaximumWidth(520); row.addWidget(self.name_edit)
        save = QPushButton("СОХРАНИТЬ ПРОФИЛЬ"); save.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF;"); save.clicked.connect(self._save_profile); row.addWidget(save); row.addStretch(); layout.addLayout(row)
        hint = QLabel("Это имя отображается только в вашем локальном профиле."); hint.setObjectName("muted"); layout.addWidget(hint); layout.addStretch(); return tab

    def _build_favorites_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); self.favorites_empty = QLabel(); self.favorites_empty.setObjectName("muted"); layout.addWidget(self.favorites_empty)
        self.favorites_table = self._table(("Тип", "Название", "Категория", "Подгруппа", "Моя оценка", "Общая оценка", "Статус")); layout.addWidget(self.favorites_table, 1); return tab

    def _build_ratings_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); self.ratings_empty = QLabel(); self.ratings_empty.setObjectName("muted"); layout.addWidget(self.ratings_empty)
        self.ratings_table = self._table(("Тип", "Название", "Категория", "Подгруппа", "Моя оценка", "Общая оценка", "Статус")); layout.addWidget(self.ratings_table, 1); return tab

    def _build_statistics_tab(self) -> QWidget:
        self.statistics_dashboard = StatisticsDashboard(); return self.statistics_dashboard

    @staticmethod
    def _table(headers) -> QTableWidget:
        table = QTableWidget(0, len(headers)); table.setHorizontalHeaderLabels(headers); table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); table.setSortingEnabled(True)
        table.verticalHeader().hide(); table.setShowGrid(False); table.setAlternatingRowColors(True); table.setWordWrap(False)
        table.horizontalHeader().setSectionsClickable(True); table.horizontalHeader().setSortIndicatorShown(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(len(headers)):
            if column != 1: table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setMouseTracking(True)
        table.setStyleSheet("""
            QTableWidget { background:#071016; alternate-background-color:#0A141C; border:1px solid #22313B; border-radius:8px; selection-background-color:#17102B; }
            QTableWidget::item { min-height:38px; padding:8px 10px; border-bottom:1px solid #1B2831; }
            QTableWidget::item:selected { border-top:1px solid #8B2CF5; border-bottom:1px solid #8B2CF5; color:white; }
            QHeaderView::section { background:#0B141C; color:#AEB8C1; border:0; border-bottom:1px solid #2A3944; padding:10px 8px; font-weight:600; }
        """)
        return table

    def refresh(self, games) -> None:
        self.games = list(games); profile = self.repository.load_profile(); self.profile_name.setText(profile.display_name); self.name_edit.setText(profile.display_name)
        self._pending_avatar_path = profile.avatar_path; self.avatar_preview.set_avatar(profile.avatar_path); self.overview.refresh(profile, self.games)
        favorites = [game for game in self.games if game.favorite]
        rated = [game for game in self.games if game.personal_score != "—"]
        self.favorites_table.setSortingEnabled(False); self.ratings_table.setSortingEnabled(False)
        self._fill(self.favorites_table, [(g.media_type, g.title, g.category, g.subgroup or "—", g.personal_score, g.general_score, g.status) for g in favorites])
        self._fill(self.ratings_table, [(g.media_type, g.title, g.category, g.subgroup or "—", g.personal_score, g.general_score, g.status) for g in rated])
        self._bind_links(self.favorites_table, favorites)
        self._bind_links(self.ratings_table, rated)
        self.favorites_table.setSortingEnabled(True); self.ratings_table.setSortingEnabled(True)
        self.favorites_empty.setText("Избранных объектов пока нет" if not favorites else f"В избранном: {len(favorites)}")
        self.ratings_empty.setText("Вы ещё ничего не оценили" if not rated else f"Оценено: {len(rated)}")
        started = [g for g in self.games if g.status != "НЕ НАЧИНАЛ"]
        completed = [g for g in self.games if g.status == "ПРОШЁЛ"]
        average = sum(float(g.personal_score) for g in rated) / len(rated) if rated else None
        self.statistics_dashboard.refresh(self.games)

    def show_overview(self) -> None:
        self.tabs.setCurrentIndex(0)

    @staticmethod
    def _fill(table: QTableWidget, rows) -> None:
        sorting = table.isSortingEnabled(); table.setSortingEnabled(False)
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            table.setRowHeight(row_index, 46)
            for column, value in enumerate(values):
                item = SortableItem(str(value));
                if column in (4, 5): item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 0: item.setForeground(__import__('PySide6.QtGui',fromlist=['QColor']).QColor('#B67AFF'))
                if column == 6:
                    colors={"ПРОШЁЛ":"#18D647","ПРОХОЖУ":"#FFC400","БРОСИЛ":"#FF4B45","НЕ НАЧИНАЛ":"#89949E"}; item.setForeground(__import__('PySide6.QtGui',fromlist=['QColor']).QColor(colors.get(str(value),'#C8D0D7')))
                table.setItem(row_index, column, item)
        table.setSortingEnabled(sorting)

    def _bind_links(self, table: QTableWidget, games) -> None:
        for row, game in enumerate(games):
            title = table.item(row, 1)
            if title is not None:
                title.setData(Qt.ItemDataRole.UserRole, game.catalog_id)
                title.setToolTip(catalog_uri(game.catalog_id))
        if not table.property("profileLinksConnected"):
            table.cellClicked.connect(lambda row, column, source=table: self._open_link(source, row, column))
            table.cellEntered.connect(lambda row, column, source=table: self._hover_link(source, row, column))
            table.setProperty("profileLinksConnected", True)

    def _open_link(self, table: QTableWidget, row: int, column: int) -> None:
        if column != 1: return
        item = table.item(row, column)
        catalog_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if catalog_id:
            self.catalog_item_requested.emit(catalog_id)

    @staticmethod
    def _hover_link(table: QTableWidget, row: int, column: int) -> None:
        from PySide6.QtGui import QColor, QCursor
        for current_row in range(table.rowCount()):
            title = table.item(current_row, 1)
            if title: title.setForeground(QColor("#F1F2F4"))
        if column == 1:
            item = table.item(row, column)
            if item: item.setForeground(QColor("#B56CFF"))
            table.viewport().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            table.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def _choose_avatar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите аватар", "", "Изображения (*.png *.jpg *.jpeg *.webp)")
        if path:
            self._pending_avatar_path = path
            self.avatar_preview.set_avatar(path)

    def _remove_avatar(self) -> None:
        self._pending_avatar_path = ""
        self.avatar_preview.set_avatar("")

    def _save_profile(self) -> None:
        name = self.name_edit.text().strip() or "Пользователь"
        current = self.repository.load_profile()
        avatar_path = store_profile_avatar(self._pending_avatar_path) if self._pending_avatar_path else ""
        profile = LocalProfile(name, current.bio, avatar_path)
        self.repository.save_profile(profile); self.profile_name.setText(name)
        self._pending_avatar_path = avatar_path; self.avatar_preview.set_avatar(avatar_path); self.overview.refresh(profile, self.games)
