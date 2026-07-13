from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import ACCENT, SUCCESS, WARNING
from app.models.game import GameData


class GameDetailPage(QScrollArea):
    favorite_changed = Signal(object, bool)
    rate_requested = Signal(object)
    status_changed = Signal(object, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.game: GameData | None = None
        self.setWidgetResizable(True)
        self.setObjectName("gameDetailPage")
        content = QWidget(); self.root = QVBoxLayout(content)
        self.root.setContentsMargins(24, 18, 24, 28); self.root.setSpacing(18)

        self.breadcrumb = QLabel("ИГРЫ  /  ШУТЕРЫ")
        self.breadcrumb.setObjectName("muted"); self.root.addWidget(self.breadcrumb)
        hero = QHBoxLayout(); hero.setSpacing(22)
        self.cover = QLabel("ОБЛОЖКА"); self.cover.setFixedSize(250, 350); self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#202A35; border:1px solid #35424E; border-radius:9px; color:#7D8994;")
        hero.addWidget(self.cover)
        info = QVBoxLayout(); info.setSpacing(10)
        title_row = QHBoxLayout(); self.title = QLabel(); self.title.setStyleSheet("font-size:27pt; font-weight:650;")
        title_row.addWidget(self.title); title_row.addStretch()
        self.favorite = QPushButton(); self.favorite.setMinimumSize(170, 40); self.favorite.clicked.connect(self._toggle_favorite); title_row.addWidget(self.favorite)
        info.addLayout(title_row)
        personal_actions = QHBoxLayout()
        self.rate_button = QPushButton("ОЦЕНИТЬ ИГРУ"); self.rate_button.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF; font-weight:600;")
        self.rate_button.clicked.connect(lambda: self.game is not None and self.rate_requested.emit(self.game))
        self.status_badge = QPushButton(); self.status_badge.setMinimumSize(170, 38)
        from app.ui.catalog.status_menu import build_status_menu
        self.status_badge.setMenu(build_status_menu(self.status_badge, self._change_status))
        personal_actions.addWidget(self.rate_button); personal_actions.addWidget(self.status_badge); personal_actions.addStretch(); info.addLayout(personal_actions)
        self.route = QLabel(); self.route.setStyleSheet(f"color:{ACCENT}; font-size:11pt;"); info.addWidget(self.route)
        self.metadata = QGridLayout(); self.metadata.setHorizontalSpacing(34); self.metadata.setVerticalSpacing(12)
        self.meta_values = {}
        self.meta_captions = {}
        for index, key in enumerate(("Разработчик", "Издатель", "Год выхода", "Платформы", "Количество игроков", "Возраст")):
            row, column = divmod(index, 2); caption = QLabel(key.upper()); caption.setObjectName("caption")
            value = QLabel(); value.setWordWrap(True); value.setStyleSheet("font-size:11pt; font-weight:500;")
            box = QVBoxLayout(); box.addWidget(caption); box.addWidget(value); self.metadata.addLayout(box, row, column); self.meta_values[key] = value; self.meta_captions[key] = caption
        info.addLayout(self.metadata)
        self.description = QLabel(); self.description.setWordWrap(True); self.description.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.description.setStyleSheet("font-size:11pt; line-height:1.4; color:#CAD1D7;"); info.addWidget(self.description, 1)
        hero.addLayout(info, 1); self.root.addLayout(hero)

        self.official_title = QLabel("ОФИЦИАЛЬНЫЕ СВЕДЕНИЯ")
        self.official_title.setStyleSheet("font-size:15pt; font-weight:600;")
        self.root.addWidget(self.official_title)
        self.official_details = QGridLayout(); self.official_details.setSpacing(12)
        self.root.addLayout(self.official_details)

        ratings_title = QLabel("ОЦЕНКИ И ИСТОЧНИКИ"); ratings_title.setStyleSheet("font-size:15pt; font-weight:600;"); self.root.addWidget(ratings_title)
        ratings = QHBoxLayout(); ratings.setSpacing(12)
        self.general_card, self.general_value = self._score_card("СРЕДНЯЯ ОЦЕНКА", "VELORA", SUCCESS); ratings.addWidget(self.general_card)
        self.personal_card, self.personal_value = self._score_card("МОЯ ОЦЕНКА", "ЛИЧНАЯ", WARNING); ratings.addWidget(self.personal_card)
        self.critic_values = {}
        self.source_cards = []
        brand_colors = {"Metacritic":"#F5C542", "IGN":"#F44336", "DualShockers":"#4DA3FF", "PC Gamer":"#E53935"}
        for source, color in brand_colors.items():
            card, value = self._score_card(source.upper(), source, color); self.critic_values[source] = value; self.source_cards.append((card, value)); ratings.addWidget(card)
        self.root.addLayout(ratings)

        lower = QHBoxLayout(); lower.setSpacing(14)
        self.stats = self._panel("МОЯ СТАТИСТИКА"); self.stats_text = QLabel(); self.stats_text.setWordWrap(True); self.stats.layout().addWidget(self.stats_text); lower.addWidget(self.stats, 1)
        self.criteria = self._panel("КРИТЕРИИ МОЕЙ ОЦЕНКИ"); self.criteria_text = QLabel(); self.criteria_text.setWordWrap(True); self.criteria.layout().addWidget(self.criteria_text); lower.addWidget(self.criteria, 1)
        self.activity = self._panel("ИСТОРИЯ ИЗМЕНЕНИЙ"); self.activity_text = QLabel(); self.activity_text.setWordWrap(True); self.activity.layout().addWidget(self.activity_text); lower.addWidget(self.activity, 1)
        self.root.addLayout(lower)
        self.root.addStretch(); self.setWidget(content)

    @staticmethod
    def _score_card(title: str, brand: str, color: str):
        card = QFrame(); card.setStyleSheet("QFrame { background:#09131A; border:1px solid #273640; border-radius:8px; }")
        layout = QVBoxLayout(card); layout.setContentsMargins(14, 12, 14, 12)
        logo = QLabel(brand); logo.setAlignment(Qt.AlignmentFlag.AlignCenter); logo.setStyleSheet(f"color:{color}; font-size:10pt; font-weight:800; border:0;")
        caption = QLabel(title); caption.setAlignment(Qt.AlignmentFlag.AlignCenter); caption.setObjectName("caption")
        value = QLabel(); value.setAlignment(Qt.AlignmentFlag.AlignCenter); value.setStyleSheet(f"color:{color}; font-size:25pt; font-weight:700; border:0;")
        layout.addWidget(logo); layout.addWidget(caption); layout.addWidget(value); return card, value

    @staticmethod
    def _panel(title: str) -> QFrame:
        panel = QFrame(); panel.setStyleSheet("QFrame { background:#081118; border:1px solid #26343E; border-radius:8px; }")
        layout = QVBoxLayout(panel); heading = QLabel(title); heading.setObjectName("caption"); layout.addWidget(heading); return panel

    def set_game(self, game: GameData) -> None:
        from app.ui.catalog.status_menu import build_status_menu
        self.status_badge.setMenu(build_status_menu(self.status_badge, self._change_status, game.media_type))
        self.game = game; self.title.setText(game.title); self.route.setText(f"{game.category}  •  {game.subgroup or 'Без подгруппы'}")
        self.breadcrumb.setText(f"{game.media_type.upper()}  /  {game.category.upper()}  /  {(game.subgroup or 'КАРТОЧКА').upper()}")
        values = {"Разработчик":game.developer, "Издатель":game.publisher, "Год выхода":game.year, "Платформы":game.platform, "Количество игроков":game.mode, "Возраст":f"{game.age_rating}+"}
        labels = {
            "Игры": ("РАЗРАБОТЧИК", "ИЗДАТЕЛЬ", "ПЛАТФОРМЫ", "КОЛИЧЕСТВО ИГРОКОВ"),
            "Фильмы": ("РЕЖИССЁР", "СТУДИЯ", "ГДЕ СМОТРЕТЬ", "ДЛИТЕЛЬНОСТЬ"),
            "Сериалы": ("СОЗДАТЕЛЬ", "СТУДИЯ", "ГДЕ СМОТРЕТЬ", "КОЛИЧЕСТВО СЕЗОНОВ"),
            "Программы": ("РАЗРАБОТЧИК", "ИЗДАТЕЛЬ", "ПЛАТФОРМЫ", "ТИП"),
        }[game.media_type]
        for key, text in zip(("Разработчик","Издатель","Платформы","Количество игроков"), labels): self.meta_captions[key].setText(text)
        for key, value in values.items(): self.meta_values[key].setText(value or "—")
        self.description.setText(game.description or "Описание для этого объекта пока не добавлено в Velora Studio.")
        self._fill_official_details(game)
        self.general_value.setText(self._score(game.general_score)); self.personal_value.setText(self._score(game.personal_score))
        self.rate_button.setText("ИЗМЕНИТЬ ОЦЕНКУ" if game.personal_score != "—" else "ОЦЕНИТЬ")
        self.status_badge.setText(game.status)
        self._style_status(game.status)
        sources = list(game.critic_scores.items())
        for index, (card, label) in enumerate(self.source_cards):
            card.setVisible(index < len(sources))
            if index < len(sources):
                source, value = sources[index]
                labels = card.findChildren(QLabel)
                if labels:
                    labels[0].setText(source)
                if len(labels) > 1:
                    labels[1].setText(source.upper())
                label.setText("—" if value is None else f"{value:.1f}")
        playtime_text = f"{game.playtime_hours:g} ч" if game.playtime_hours else "—"
        watched_episodes = sum(state == "watched" for state in game.episode_states.values())
        interaction = {"Игры":f"Время в игре: {playtime_text}", "Программы":f"Время использования: {playtime_text}", "Фильмы":f"Просмотров: {game.watch_count}", "Сериалы":f"Просмотрено серий: {watched_episodes}/{max(1, game.seasons or 1) * 10}"}[game.media_type]
        self.stats_text.setText(f"Статус: {game.status}\n{interaction}\nИзбранное: {'Да' if game.favorite else 'Нет'}\nДобавлено: 12.05.2024")
        self.criteria_text.setText("\n".join(f"{name}: {value}/10" for name, value in game.rating_criteria.items()) or "Личная оценка ещё не заполнена")
        self.activity_text.setText("\n".join(reversed(game.history[-5:])) or "Изменений пока нет")
        self.favorite.setText("★ В ИЗБРАННОМ" if game.favorite else "☆ В ИЗБРАННОЕ")
        self._set_cover(game.cover_path)

    def _fill_official_details(self, game: GameData) -> None:
        while self.official_details.count():
            item = self.official_details.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        entries: list[tuple[str, str]] = []
        budget_title = "БЮДЖЕТ СЪЁМОК" if game.media_type in ("Фильмы", "Сериалы") else "БЮДЖЕТ РАЗРАБОТКИ"
        entries.append((budget_title, self._format_budget(game.budget_amount, game.budget_currency)))
        if game.publisher_countries: entries.append(("СТРАНА ИЗДАТЕЛЯ", ", ".join(game.publisher_countries)))
        if game.interface_languages: entries.append(("ЯЗЫКИ ИНТЕРФЕЙСА", ", ".join(game.interface_languages)))
        if game.awards: entries.append(("НАГРАДЫ И ПРЕМИИ", "\n".join(f"• {value}" for value in game.awards)))
        if game.dlc: entries.append(("DLC", "\n".join(f"• {value}" for value in game.dlc)))
        if game.cast:
            entries.append(("В ГЛАВНЫХ РОЛЯХ", "\n".join(f"{entry.get('actor','')} — {entry.get('role','')}" for entry in game.cast)))
        if game.system_requirements:
            names={"os_min":"ОС (мин.)","os_rec":"ОС (рек.)","cpu_min":"Процессор (мин.)","cpu_rec":"Процессор (рек.)","gpu_min":"Видеокарта (мин.)","gpu_rec":"Видеокарта (рек.)","ram_min":"Память (мин.)","ram_rec":"Память (рек.)","storage":"На диске"}
            entries.append(("СИСТЕМНЫЕ ТРЕБОВАНИЯ", "\n".join(f"{names.get(key,key)}: {value}" for key,value in game.system_requirements.items())))
        if game.source_code_type: entries.append(("ИСХОДНЫЙ КОД", game.source_code_type))
        if game.architectures: entries.append(("АРХИТЕКТУРЫ", ", ".join(game.architectures)))
        if game.programming_languages: entries.append(("ЯЗЫКИ РАЗРАБОТКИ", ", ".join(game.programming_languages)))
        if game.distribution_model: entries.append(("РАСПРОСТРАНЕНИЕ", game.distribution_model))
        if game.stores: entries.append(("МАГАЗИНЫ", ", ".join(game.stores)))
        self.official_title.setVisible(bool(entries))
        for index,(title,text) in enumerate(entries):
            panel=self._panel(title); value=QLabel(text); value.setWordWrap(True); value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setStyleSheet("color:#CAD1D7; border:0; line-height:1.35;"); panel.layout().addWidget(value)
            self.official_details.addWidget(panel,index//3,index%3)
        for column in range(3): self.official_details.setColumnStretch(column,1)

    @staticmethod
    def _format_budget(amount: float | None, currency: str) -> str:
        if amount is None:
            return "—"
        absolute = abs(amount)
        if absolute >= 1_000_000_000:
            value, suffix = amount / 1_000_000_000, "млрд"
        elif absolute >= 1_000_000:
            value, suffix = amount / 1_000_000, "млн"
        elif absolute >= 1_000:
            value, suffix = amount / 1_000, "тыс."
        else:
            value, suffix = amount, ""
        number = f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
        return " ".join(part for part in (number, suffix, currency) if part)

    def _set_cover(self, cover_path: str) -> None:
        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path); self.cover.setPixmap(pixmap.scaled(self.cover.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else: self.cover.setPixmap(QPixmap()); self.cover.setText("ОБЛОЖКА\nбудет добавлена через Studio")

    def _toggle_favorite(self) -> None:
        if self.game is None: return
        self.game.favorite = not self.game.favorite; self.favorite.setText("★ В ИЗБРАННОМ" if self.game.favorite else "☆ В ИЗБРАННОЕ")
        self.stats_text.setText(self.stats_text.text().replace("Избранное: Нет", "Избранное: Да") if self.game.favorite else self.stats_text.text().replace("Избранное: Да", "Избранное: Нет"))
        self.favorite_changed.emit(self.game, self.game.favorite)

    def _change_status(self, status: str) -> None:
        if self.game is None:
            return
        self.game.status = status
        self.game.history.append(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} — статус: {status}")
        # Refresh every dependent element together: badge, statistics and
        # activity history. Partial text replacements caused stale UI state.
        self.set_game(self.game)
        self.status_changed.emit(self.game, status)

    def _style_status(self, status: str) -> None:
        from app.ui.catalog.status_menu import status_visual
        color, border, background = status_visual(status)
        self.status_badge.setStyleSheet(f"color:{color}; border:1px solid {border}; background:{background}; border-radius:6px; font-weight:600; padding:6px 24px 6px 10px;")

    @staticmethod
    def _score(value: str) -> str:
        try: return f"{float(value):.1f}"
        except ValueError: return "—"
