from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import ACCENT, SUCCESS, WARNING
from app.core.paths import resolve_resource_path
from app.models.game import GameData
from app.core.icon_registry import IconRegistry
from app.ui.widgets.platform_icons import PlatformIconRow
from app.ui.widgets.age_rating import AgeRatingValue
from app.ui.widgets.critic_sources import apply_source_logo, source_brand_color, source_slots
from app.core.display_text import compact_entities
from app.ui.game_detail.system_requirements_panel import SystemRequirementsPanel
from app.ui.game_detail.chronology_panel import ChronologyPanel


class GameDetailPage(QScrollArea):
    favorite_changed = Signal(object, bool)
    rate_requested = Signal(object)
    status_changed = Signal(object, str)
    catalog_item_requested = Signal(str)

    def __init__(self, repository=None, parent=None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.game: GameData | None = None
        self._status_menu_media_type = ""
        self.setWidgetResizable(True)
        self.setObjectName("gameDetailPage")
        content = QWidget(); self.root = QVBoxLayout(content)
        self.root.setContentsMargins(24, 18, 24, 28); self.root.setSpacing(18)

        self.breadcrumb = QLabel("ИГРЫ  /  ШУТЕРЫ")
        self.breadcrumb.setObjectName("muted"); self.root.addWidget(self.breadcrumb)
        hero = QHBoxLayout(); hero.setSpacing(22)
        self.cover = QLabel("ОБЛОЖКА"); self.cover.setFixedSize(210, 315); self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#18212A; border:1px solid #2B3640; border-radius:4px; color:#7D8994;")
        hero.addWidget(self.cover)
        info = QVBoxLayout(); info.setSpacing(10)
        title_row = QHBoxLayout(); self.title = QLabel(); self.title.setStyleSheet("font-size:27pt; font-weight:650;")
        title_row.addWidget(self.title); title_row.addStretch()
        self.favorite = QPushButton(); self.favorite.setMinimumSize(170, 40); self.favorite.clicked.connect(self._toggle_favorite); title_row.addWidget(self.favorite)
        info.addLayout(title_row)
        personal_actions = QHBoxLayout()
        self.rate_button = QPushButton("ОЦЕНИТЬ ИГРУ"); self.rate_button.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF; font-weight:600;")
        self.rate_button.setIcon(IconRegistry.icon("edit", category="ui")); self.rate_button.setIconSize(QSize(17, 17))
        self.rate_button.clicked.connect(lambda: self.game is not None and self.rate_requested.emit(self.game))
        self.status_badge = QPushButton(); self.status_badge.setMinimumSize(170, 38)
        self.status_badge.setIcon(IconRegistry.icon("history_recent", variant="dark", category="ui")); self.status_badge.setIconSize(QSize(16, 16))
        from app.ui.catalog.status_menu import build_status_menu
        self.status_badge.setMenu(build_status_menu(self.status_badge, self._change_status))
        self.tags_button=QPushButton("ТЕГИ"); self.tags_button.clicked.connect(self._edit_tags)
        personal_actions.addWidget(self.rate_button); personal_actions.addWidget(self.status_badge); personal_actions.addWidget(self.tags_button); personal_actions.addStretch(); info.addLayout(personal_actions)
        self.route = QLabel(); self.route.setStyleSheet(f"color:{ACCENT}; font-size:11pt;"); info.addWidget(self.route)
        self.tags_widget = QWidget()
        self.tags_grid = QGridLayout(self.tags_widget)
        self.tags_grid.setContentsMargins(0, 0, 0, 0)
        self.tags_grid.setHorizontalSpacing(7)
        self.tags_grid.setVerticalSpacing(6)
        info.addWidget(self.tags_widget)
        self.metadata = QGridLayout(); self.metadata.setHorizontalSpacing(34); self.metadata.setVerticalSpacing(12)
        self.meta_values = {}
        self.meta_captions = {}
        meta_icons = {
            "Разработчик": ("code_display", "ui", "svg"),
            "Издатель": ("announcement", "marketing", "dark"),
            "Год выхода": ("clock", "ui", "dark"),
            "Платформы": ("gaming_pc", "platforms", "dark"),
            "Количество игроков": ("play", "ui", "dark"),
        }
        for index, key in enumerate(("Разработчик", "Издатель", "Год выхода", "Платформы", "Количество игроков", "Возраст")):
            row, column = divmod(index, 2); caption = QLabel(key.upper()); caption.setObjectName("caption")
            if key == "Платформы":
                value = PlatformIconRow(colored=False)
            elif key == "Возраст":
                value = AgeRatingValue()
            else:
                value = QLabel(); value.setWordWrap(True); value.setStyleSheet("font-size:11pt; font-weight:500;")
            caption_row = QHBoxLayout(); caption_row.setContentsMargins(0, 0, 0, 0); caption_row.setSpacing(5)
            if key in meta_icons:
                icon_id, category, variant = meta_icons[key]
                caption_icon = QLabel(); caption_icon.setFixedSize(18, 18)
                caption_icon.setPixmap(IconRegistry.pixmap(icon_id, 16, variant=variant, category=category))
                caption_row.addWidget(caption_icon)
            caption_row.addWidget(caption); caption_row.addStretch(1)
            box = QVBoxLayout(); box.addLayout(caption_row); box.addWidget(value); self.metadata.addLayout(box, row, column); self.meta_values[key] = value; self.meta_captions[key] = caption
        info.addLayout(self.metadata)
        self.description = QLabel(); self.description.setWordWrap(True); self.description.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.description.setStyleSheet("font-size:11pt; line-height:1.4; color:#CAD1D7;"); info.addWidget(self.description, 1)
        hero.addLayout(info, 1); self.root.addLayout(hero)

        self.official_title = QLabel("ОФИЦИАЛЬНЫЕ СВЕДЕНИЯ")
        self.official_title.setStyleSheet("font-size:15pt; font-weight:600;")
        self.root.addWidget(self.official_title)
        self.official_details = QGridLayout(); self.official_details.setSpacing(12)
        self.root.addLayout(self.official_details)
        self.requirements_panel = SystemRequirementsPanel()
        self.root.addWidget(self.requirements_panel)
        self.chronology_panel = ChronologyPanel()
        self.chronology_panel.catalog_item_requested.connect(self.catalog_item_requested.emit)
        self.root.addWidget(self.chronology_panel)

        ratings_title = QLabel("ОЦЕНКИ И ИСТОЧНИКИ"); ratings_title.setStyleSheet("font-size:15pt; font-weight:600;"); self.root.addWidget(ratings_title)
        ratings = QHBoxLayout(); ratings.setSpacing(12)
        self.general_card, self.general_value = self._score_card("СРЕДНЯЯ ОЦЕНКА", "VELORA", SUCCESS); ratings.addWidget(self.general_card)
        self.personal_card, self.personal_value = self._score_card("МОЯ ОЦЕНКА", "ЛИЧНАЯ", WARNING); ratings.addWidget(self.personal_card)
        self.critic_values = {}
        self.source_cards = []
        initial_sources = ("Metacritic", "IGN", "DualShockers", "PC Gamer")
        for source in initial_sources:
            color = source_brand_color(source)
            card, value = self._score_card(source.upper(), source, color); self.critic_values[source] = value; self.source_cards.append((card, value)); ratings.addWidget(card)
        self.root.addLayout(ratings)

        lower = QHBoxLayout(); lower.setSpacing(14)
        self.stats = self._panel("МОЯ СТАТИСТИКА"); self.stats_text = QLabel(); self.stats_text.setWordWrap(True); self.stats.layout().addWidget(self.stats_text); lower.addWidget(self.stats, 1)
        self.criteria = self._panel("КРИТЕРИИ МОЕЙ ОЦЕНКИ"); self.criteria_text = QLabel(); self.criteria_text.setWordWrap(True); self.criteria.layout().addWidget(self.criteria_text); lower.addWidget(self.criteria, 1)
        self.activity = self._panel("ИСТОРИЯ ИЗМЕНЕНИЙ"); self.activity_text = QLabel(); self.activity_text.setWordWrap(True); self.activity.layout().addWidget(self.activity_text); lower.addWidget(self.activity, 1)
        self.root.addLayout(lower)
        self.root.addStretch(); self.setWidget(content)

    def _edit_tags(self) -> None:
        if not self.game or not self.repository:return
        from app.ui.dialogs.tag_editor_dialog import TagEditorDialog
        if TagEditorDialog(self.repository,self.game.catalog_id,self).exec():
            names={tag_id:name for tag_id,name,color,count in self.repository.tags()}; self.game.tags=[names[tag_id] for tag_id in self.repository.tag_ids_for(self.game.catalog_id) if tag_id in names]
            self._render_tags(self.game)

    @staticmethod
    def _score_card(title: str, brand: str, color: str):
        card = QFrame(); card.setObjectName("ratingSourceCard"); card.setStyleSheet("QFrame#ratingSourceCard { background:#09131A; border:1px solid #273640; border-radius:8px; }")
        layout = QVBoxLayout(card); layout.setContentsMargins(14, 12, 14, 12)
        logo = QLabel(); logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setProperty("criticSourceLogo", True)
        if brand not in {"VELORA", "ЛИЧНАЯ"}:
            apply_source_logo(logo, brand, QSize(42, 26))
        else:
            logo.setText(brand)
            logo.setStyleSheet(f"color:{color}; font-size:10pt; font-weight:800; border:0;")
        caption = QLabel(title); caption.setAlignment(Qt.AlignmentFlag.AlignCenter); caption.setObjectName("caption")
        value = QLabel(); value.setAlignment(Qt.AlignmentFlag.AlignCenter); value.setStyleSheet(f"color:{color}; font-size:25pt; font-weight:700; border:0;")
        layout.addWidget(logo); layout.addWidget(caption); layout.addWidget(value); return card, value

    @staticmethod
    def _panel(title: str) -> QFrame:
        panel = QFrame(); panel.setObjectName("officialInfoCard"); panel.setStyleSheet("QFrame#officialInfoCard { background:#081118; border:1px solid #26343E; border-radius:8px; }")
        layout = QVBoxLayout(panel); heading_row = QHBoxLayout(); heading_row.setContentsMargins(0, 0, 0, 0)
        icon_map = {
            "БЮДЖЕТ": ("film_budget", "media", "dark"), "СТРАНА": ("globe", "ui", "dark"),
            "ЯЗЫКИ ИНТЕРФЕЙСА": ("globe", "ui", "dark"), "НАГРАДЫ": ("trophy", "achievements", "dark"),
            "DLC": ("media_file", "media", "dark"), "СИСТЕМНЫЕ": ("processor", "hardware", "dark"),
            "ИСХОДНЫЙ": ("code_display", "ui", "svg"), "АРХИТЕКТУРЫ": ("ai_chip", "hardware", "dark"),
            "ЯЗЫКИ РАЗРАБОТКИ": ("python", "brands", "svg"), "РАСПРОСТРАНЕНИЕ": ("announcement", "marketing", "dark"),
            "МАГАЗИНЫ": ("storefront", "stores", "svg"),
        }
        match = next((value for prefix, value in icon_map.items() if title.startswith(prefix)), None)
        if match:
            icon_id, category, variant = match; icon = QLabel(); icon.setFixedSize(18, 18)
            icon.setPixmap(IconRegistry.pixmap(icon_id, 16, variant=variant, category=category)); heading_row.addWidget(icon)
        heading = QLabel(title); heading.setObjectName("caption"); heading_row.addWidget(heading); heading_row.addStretch(); layout.addLayout(heading_row); return panel

    def set_game(self, game: GameData) -> None:
        from app.ui.catalog.status_menu import build_status_menu
        if self._status_menu_media_type != game.media_type:
            previous_menu = self.status_badge.menu()
            self.status_badge.setMenu(
                build_status_menu(self.status_badge, self._change_status, game.media_type)
            )
            self._status_menu_media_type = game.media_type
            if previous_menu is not None:
                previous_menu.deleteLater()
        self.game = game; self.title.setText(game.title); self.route.setText(f"{game.category}  •  {game.subgroup or 'Без подгруппы'}"); self._render_tags(game)
        self.breadcrumb.setText(f"{game.media_type.upper()}  /  {game.category.upper()}  /  {(game.subgroup or 'КАРТОЧКА').upper()}")
        developer_text, developer_tooltip = compact_entities(game.developer)
        publisher_text, publisher_tooltip = compact_entities(game.publisher)
        values = {"Разработчик":developer_text, "Издатель":publisher_text, "Год выхода":game.year, "Платформы":game.platform, "Количество игроков":game.mode, "Возраст":game.age_rating}
        labels = {
            "Игры": ("РАЗРАБОТЧИК", "ИЗДАТЕЛЬ", "ПЛАТФОРМЫ", "КОЛИЧЕСТВО ИГРОКОВ"),
            "Фильмы": ("РЕЖИССЁР", "СТУДИЯ", "ГДЕ СМОТРЕТЬ", "ДЛИТЕЛЬНОСТЬ"),
            "Сериалы": ("СОЗДАТЕЛЬ", "СТУДИЯ", "ГДЕ СМОТРЕТЬ", "КОЛИЧЕСТВО СЕЗОНОВ"),
            "Программы": ("РАЗРАБОТЧИК", "ИЗДАТЕЛЬ", "ПЛАТФОРМЫ", "ТИП"),
        }.get(game.media_type, ("СОЗДАТЕЛЬ", "ИЗДАТЕЛЬ", "ПЛАТФОРМА", "ФОРМАТ"))
        for key, text in zip(("Разработчик","Издатель","Платформы","Количество игроков"), labels): self.meta_captions[key].setText(text)
        for key, value in values.items(): self.meta_values[key].setText(value or "—")
        self.meta_values["Разработчик"].setToolTip(developer_tooltip)
        self.meta_values["Издатель"].setToolTip(publisher_tooltip)
        self.description.setText(game.description or "Описание для этого объекта пока не добавлено в Velora Studio.")
        self._fill_official_details(game)
        self.chronology_panel.set_chronology(
            game.franchise_name, game.chronology, game.catalog_id
        )
        self.general_value.setText(self._score(game.general_score)); self.personal_value.setText(self._score(game.personal_score))
        self.rate_button.setText("ИЗМЕНИТЬ ОЦЕНКУ" if game.personal_score != "—" else "ОЦЕНИТЬ")
        self.status_badge.setText(game.status)
        self._style_status(game.status)
        sources = source_slots(
            game.media_type,
            game.critic_scores,
            limit=len(self.source_cards),
        )
        for index, (card, label) in enumerate(self.source_cards):
            card.setVisible(index < len(sources))
            if index < len(sources):
                source, value = sources[index]
                labels = card.findChildren(QLabel)
                if labels:
                    apply_source_logo(labels[0], source, QSize(42, 26))
                if len(labels) > 1:
                    labels[1].setText(source.upper())
                label.setStyleSheet(
                    f"color:{source_brand_color(source)}; "
                    "font-size:25pt; font-weight:700; border:0;"
                )
                label.setText("—" if value is None else f"{value:.1f}")
        playtime_text = f"{game.playtime_hours:g} ч" if game.playtime_hours else "—"
        watched_episodes = sum(state == "watched" for state in game.episode_states.values())
        interaction = {
            "Игры": f"Время в игре: {playtime_text}",
            "Программы": "История использования хранится по статусам",
            "Фильмы": f"Просмотров: {game.watch_count}",
            "Сериалы": f"Прогресс: сезон {game.season_number or '—'}, серия {game.episode_number or '—'}",
        }.get(game.media_type, "Локальный пользовательский объект")
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
        self.requirements_panel.set_requirements(
            game.system_requirements,
            visible=game.media_type == "Игры",
        )
        if game.media_type != "Игры":
            budget_title = "БЮДЖЕТ СЪЁМОК" if game.media_type in ("Фильмы", "Сериалы") else "БЮДЖЕТ РАЗРАБОТКИ"
            entries.append((budget_title, self._format_budget(game.budget_amount, game.budget_currency)))
        if game.publisher_countries: entries.append(("СТРАНА ИЗДАТЕЛЯ", ", ".join(game.publisher_countries)))
        if game.interface_languages: entries.append(("ЯЗЫКИ ИНТЕРФЕЙСА", ", ".join(game.interface_languages)))
        if game.awards: entries.append(("НАГРАДЫ И ПРЕМИИ", "\n".join(f"• {value}" for value in game.awards)))
        if game.dlc: entries.append(("DLC", "\n".join(f"• {value}" for value in game.dlc)))
        if game.cast:
            cast_lines = []
            for entry in game.cast:
                if isinstance(entry, dict):
                    actor = str(entry.get("actor", "")).strip()
                    role = str(entry.get("role", "")).strip()
                    cast_lines.append(
                        f"{actor} — {role}" if actor and role else actor or role
                    )
                else:
                    text = str(entry).strip()
                    if text:
                        cast_lines.append(text)
            if cast_lines:
                entries.append(("В ГЛАВНЫХ РОЛЯХ", "\n".join(cast_lines)))
        if game.source_code_type: entries.append(("ИСХОДНЫЙ КОД", game.source_code_type))
        if game.architectures: entries.append(("АРХИТЕКТУРЫ", ", ".join(game.architectures)))
        if game.programming_languages: entries.append(("ЯЗЫКИ РАЗРАБОТКИ", ", ".join(game.programming_languages)))
        if game.distribution_model: entries.append(("РАСПРОСТРАНЕНИЕ", game.distribution_model))
        if game.stores: entries.append(("МАГАЗИНЫ", ", ".join(game.stores)))
        self.official_title.setVisible(bool(entries))
        for index,(title,text) in enumerate(entries):
            panel=self._panel(title)
            value=QLabel(text); value.setWordWrap(True); value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            value.setStyleSheet("color:#CAD1D7; border:0; line-height:1.35;")
            if title == "DLC":
                viewport = QWidget()
                viewport.setStyleSheet("background:transparent;")
                viewport_layout = QVBoxLayout(viewport)
                viewport_layout.setContentsMargins(0, 0, 0, 0)
                viewport_layout.addWidget(value)
                viewport_layout.addStretch(1)
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setStyleSheet("QScrollArea { background:transparent; border:0; } QScrollArea > QWidget > QWidget { background:transparent; }")
                scroll.setMinimumHeight(58)
                scroll.setMaximumHeight(132)
                scroll.setWidget(viewport)
                panel.layout().addWidget(scroll)
            else:
                panel.layout().addWidget(value)
            self.official_details.addWidget(panel,index//3,index%3)
        for column in range(3): self.official_details.setColumnStretch(column,1)

    def _render_tags(self, game: GameData) -> None:
        while self.tags_grid.count():
            item = self.tags_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        combined = [(tag, False) for tag in game.system_tags]
        combined.extend((tag, True) for tag in game.tags if tag not in game.system_tags)
        self.tags_button.setText(f"ТЕГИ · {len(combined)}" if combined else "ТЕГИ")
        for index, (tag, personal) in enumerate(combined):
            chip = QLabel(f"# {tag}")
            chip.setToolTip("Личный тег" if personal else "Тег официального каталога")
            if personal:
                chip.setStyleSheet(
                    "color:#E5CAFF;background:#26133D;border:1px solid #8B2CF5;"
                    "border-radius:4px;padding:4px 9px;font-weight:600;"
                )
            else:
                chip.setStyleSheet(
                    "color:#C7D0D8;background:#101A22;border:1px solid #34434E;"
                    "border-radius:4px;padding:4px 9px;"
                )
            self.tags_grid.addWidget(chip, index // 6, index % 6)
        self.tags_widget.setVisible(bool(combined))

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
        resolved_path = resolve_resource_path(cover_path) if cover_path else None
        if resolved_path and resolved_path.is_file():
            pixmap = QPixmap(str(resolved_path)); self.cover.setPixmap(pixmap.scaled(self.cover.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
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
