from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.data.user_repository import LocalProfile, UserRepository


class ProfilePage(QWidget):
    def __init__(self, repository: UserRepository, parent=None) -> None:
        super().__init__(parent); self.repository = repository; self.games = []
        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 22); root.setSpacing(14)
        heading = QHBoxLayout(); title = QLabel("МОЙ VELORA"); title.setStyleSheet("font-family:Georgia; font-size:26pt; letter-spacing:2px;")
        heading.addWidget(title); heading.addStretch(); self.profile_name = QLabel(); self.profile_name.setStyleSheet("font-size:14pt; font-weight:600;"); heading.addWidget(self.profile_name)
        root.addLayout(heading)
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_ratings_tab(), "МОИ ОЦЕНКИ")
        self.tabs.addTab(self._build_favorites_tab(), "ИЗБРАННОЕ")
        self.tabs.addTab(self._build_statistics_tab(), "СТАТИСТИКА")
        self.tabs.addTab(self._build_profile_tab(), "ПРОФИЛЬ")
        root.addWidget(self.tabs, 1)

    def _build_profile_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(18, 22, 18, 18)
        caption = QLabel("ИМЯ ПРОФИЛЯ"); caption.setObjectName("caption"); layout.addWidget(caption)
        row = QHBoxLayout(); self.name_edit = QLineEdit(); self.name_edit.setMaximumWidth(520); row.addWidget(self.name_edit)
        save = QPushButton("СОХРАНИТЬ ИМЯ"); save.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF;"); save.clicked.connect(self._save_name); row.addWidget(save); row.addStretch(); layout.addLayout(row)
        hint = QLabel("Это имя отображается только в вашем локальном профиле."); hint.setObjectName("muted"); layout.addWidget(hint); layout.addStretch(); return tab

    def _build_favorites_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); self.favorites_empty = QLabel(); self.favorites_empty.setObjectName("muted"); layout.addWidget(self.favorites_empty)
        self.favorites_table = self._table(("Название", "Категория", "Моя оценка", "Статус")); layout.addWidget(self.favorites_table, 1); return tab

    def _build_ratings_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); self.ratings_empty = QLabel(); self.ratings_empty.setObjectName("muted"); layout.addWidget(self.ratings_empty)
        self.ratings_table = self._table(("Название", "Моя оценка", "Общая оценка", "Статус")); layout.addWidget(self.ratings_table, 1); return tab

    def _build_statistics_tab(self) -> QWidget:
        tab = QWidget(); layout = QVBoxLayout(tab); self.statistics = QLabel(); self.statistics.setAlignment(Qt.AlignmentFlag.AlignTop); self.statistics.setStyleSheet("font-size:12pt; line-height:1.5; padding:22px;")
        panel = QFrame(); panel.setStyleSheet("background:#09131A; border:1px solid #273640; border-radius:8px;"); panel_layout = QVBoxLayout(panel); panel_layout.addWidget(self.statistics); layout.addWidget(panel); layout.addStretch(); return tab

    @staticmethod
    def _table(headers) -> QTableWidget:
        table = QTableWidget(0, len(headers)); table.setHorizontalHeaderLabels(headers); table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(headers)): table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def refresh(self, games) -> None:
        self.games = list(games); profile = self.repository.load_profile(); self.profile_name.setText(profile.display_name); self.name_edit.setText(profile.display_name)
        favorites = [game for game in self.games if game.favorite]
        rated = [game for game in self.games if game.personal_score != "—"]
        self._fill(self.favorites_table, [(g.title, g.category, g.personal_score, g.status) for g in favorites])
        self._fill(self.ratings_table, [(g.title, g.personal_score, g.general_score, g.status) for g in rated])
        self.favorites_empty.setText("Избранных объектов пока нет" if not favorites else f"В избранном: {len(favorites)}")
        self.ratings_empty.setText("Вы ещё ничего не оценили" if not rated else f"Оценено: {len(rated)}")
        started = [g for g in self.games if g.status != "НЕ НАЧИНАЛ"]
        completed = [g for g in self.games if g.status == "ПРОШЁЛ"]
        average = sum(float(g.personal_score) for g in rated) / len(rated) if rated else None
        total_hours = sum(game.playtime_hours for game in self.games)
        lines = ["ОБЩАЯ СТАТИСТИКА", "", f"Объектов: {len(self.games)}", f"Оценено: {len(rated)}", f"Начато: {len(started)}", f"Завершено: {len(completed)}", f"В избранном: {len(favorites)}", f"Общее время в играх: {total_hours:g} ч", f"Средняя личная оценка: {average:.1f}" if average is not None else "Средняя личная оценка: —"]
        for media_type in ("Игры", "Фильмы", "Сериалы", "Программы"):
            objects = [game for game in self.games if game.media_type == media_type]
            media_rated = [game for game in objects if game.personal_score != "—"]
            media_favorites = [game for game in objects if game.favorite]
            lines += ["", media_type.upper(), f"Всего: {len(objects)} · Оценено: {len(media_rated)} · Избранное: {len(media_favorites)}"]
            if media_type == "Игры": lines.append(f"Время: {sum(game.playtime_hours for game in objects):g} ч")
        self.statistics.setText("\n".join(lines))

    @staticmethod
    def _fill(table: QTableWidget, rows) -> None:
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values): table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _save_name(self) -> None:
        name = self.name_edit.text().strip() or "Пользователь"
        current = self.repository.load_profile(); self.repository.save_profile(LocalProfile(name, current.bio, current.avatar_path)); self.profile_name.setText(name)
