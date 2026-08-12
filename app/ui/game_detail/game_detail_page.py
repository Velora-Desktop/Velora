from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QTabWidget, QVBoxLayout, QWidget

from app.core.constants import ACCENT, SUCCESS, WARNING
from app.core.paths import resolve_resource_path
from app.models.game import GameData
from app.core.icon_registry import IconRegistry
from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.components.animated_icon import HoverAnimatedIcon
from app.ui.widgets.platform_icons import PlatformIconRow
from app.ui.widgets.age_rating import AgeRatingValue
from app.ui.widgets.critic_sources import apply_source_logo, source_brand_color, source_slots
from app.ui.widgets.company_logo_row import CompanyLogoRow
from app.core.display_text import compact_entities
from app.ui.game_detail.system_requirements_panel import SystemRequirementsPanel
from app.ui.game_detail.chronology_panel import ChronologyPanel
from app.application.tag_service import TagService
from app.core.runtime import startup_storage
from app.ui.game_detail.tag_presenter import TagPresenter
from app.ui.rating_palette import rating_color
from app.ui.velora_ui.motion import animate_icon_pulse, apply_favorite_icon


DOOM_ETERNAL_REFERENCE_DESCRIPTION = (
    "DOOM Eternal — прямое продолжение DOOM (2016), в котором Палача Рока "
    "ждёт новое противостояние силам Ада. Игрок сочетает мощное оружие, "
    "мобильную боевую систему и способности, путешествуя по измерениям и "
    "уничтожая новых и знакомых демонов."
)


class GameDetailPage(QScrollArea):
    favorite_changed = Signal(object, bool)
    rate_requested = Signal(object)
    status_changed = Signal(object, str)
    catalog_item_requested = Signal(str)
    aw02_changed = Signal()
    tag_filter_requested = Signal(str)

    def __init__(self, repository=None, parent=None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.game: GameData | None = None
        self._status_menu_media_type = ""
        storage = startup_storage()
        self.tag_presenter = (
            TagPresenter(TagService(storage.catalog_db, storage.user_db))
            if storage else None
        )
        self.setWidgetResizable(True)
        self.setObjectName("gameDetailPage")
        content = QWidget(); self._content = content; self.root = QVBoxLayout(content)
        self.root.setContentsMargins(24, 18, 24, 28); self.root.setSpacing(18)

        self.breadcrumb = QLabel("ИГРЫ  /  ШУТЕРЫ")
        self.breadcrumb.setObjectName("muted"); self.root.addWidget(self.breadcrumb)
        hero = QHBoxLayout(); self.hero_layout = hero; hero.setSpacing(22)
        self.cover = QLabel("ОБЛОЖКА"); self.cover.setFixedSize(210, 315); self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#18212A; border:1px solid #2B3640; border-radius:4px; color:#7D8994;")
        # Keep the hero content-sized. Sparse records must not absorb the free
        # vertical space and push the tabs towards the bottom of the window.
        hero.addWidget(self.cover, 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout(); info.setSpacing(10)
        title_row = QHBoxLayout(); self.title = QLabel(); self.title.setStyleSheet("font-size:27pt; font-weight:650;")
        title_row.addWidget(self.title); title_row.addStretch()
        self.favorite = QPushButton(); self.favorite.setFixedSize(170, 40); self.favorite.setIconSize(QSize(20, 20)); self._favorite_animation = None; self.favorite.clicked.connect(self._toggle_favorite); title_row.addWidget(self.favorite)
        info.addLayout(title_row)
        personal_actions = QHBoxLayout()
        self.rate_button = QPushButton("ОЦЕНИТЬ ИГРУ"); self.rate_button.setStyleSheet("background:#6E1BC4; border:1px solid #A54BFF; font-weight:600;")
        self.rate_button.setIcon(IconRegistry.icon("edit", category="ui")); self.rate_button.setIconSize(QSize(17, 17))
        self.rate_button.clicked.connect(lambda: self.game is not None and self.rate_requested.emit(self.game))
        from app.ui.catalog.status_menu import StatusButton
        self.status_badge = StatusButton(self._change_status); self.status_badge.setMinimumSize(170, 38)
        self.status_badge.setIcon(IconRegistry.icon("history_recent", variant="dark", category="ui")); self.status_badge.setIconSize(QSize(16, 16))
        personal_actions.addWidget(self.rate_button); personal_actions.addWidget(self.status_badge); personal_actions.addStretch(); info.addLayout(personal_actions)
        self.route = QLabel(); self.route.setStyleSheet(f"color:{ACCENT}; font-size:11pt;"); info.addWidget(self.route)
        self.metadata = QGridLayout(); self.metadata.setHorizontalSpacing(34); self.metadata.setVerticalSpacing(12)
        self.meta_values = {}
        self.meta_captions = {}
        meta_icons = {
            "Разработчик": ("code_display", "ui", "svg"),
            "Издатель": ("metadata.game_support", "semantic", "dark"),
            "Год выхода": ("metadata.release", "semantic", "dark"),
            "Платформы": ("gaming_pc", "platforms", "dark"),
            "Количество игроков": ("metadata.players", "semantic", "dark"),
        }
        for index, key in enumerate(("Разработчик", "Издатель", "Год выхода", "Платформы", "Количество игроков", "Возраст")):
            row, column = divmod(index, 2); caption = QLabel(key.upper()); caption.setObjectName("caption")
            if key == "Платформы":
                value = PlatformIconRow(colored=False)
            elif key == "Возраст":
                value = AgeRatingValue()
            elif key in ("Разработчик", "Издатель"):
                value = CompanyLogoRow(max_visible=1)
            else:
                value = QLabel(); value.setWordWrap(True); value.setStyleSheet("font-size:11pt; font-weight:500;")
            caption_row = QHBoxLayout(); caption_row.setContentsMargins(0, 0, 0, 0); caption_row.setSpacing(5)
            if key in meta_icons:
                if key == "Разработчик":
                    caption_icon = HoverAnimatedIcon(
                        "animated.developer", 18, frame_interval_ms=41,
                        autoplay=True, mouse_transparent=True,
                    )
                    caption_icon.setObjectName("animatedDeveloperMetadataIcon")
                elif key == "Издатель":
                    caption_icon = QStackedWidget()
                    caption_icon.setFixedSize(18, 18)
                    publisher_icon = QLabel()
                    publisher_icon.setFixedSize(18, 18)
                    publisher_icon.setPixmap(IconProvider.pixmap(
                        "metadata.game_support", 16, "#C8D0D8"
                    ))
                    cinema_icon = HoverAnimatedIcon(
                        "animated.cinema", 18, frame_interval_ms=41,
                        autoplay=True, mouse_transparent=True,
                    )
                    cinema_icon.setObjectName("animatedStudioMetadataIcon")
                    caption_icon.addWidget(publisher_icon)
                    caption_icon.addWidget(cinema_icon)
                    self.studio_icon_stack = caption_icon
                elif key == "Платформы":
                    caption_icon = QStackedWidget()
                    caption_icon.setFixedSize(18, 18)
                    platform_icon = HoverAnimatedIcon(
                        "animated.platform", 18, frame_interval_ms=41,
                        autoplay=True, mouse_transparent=True,
                    )
                    platform_icon.setObjectName("animatedPlatformMetadataIcon")
                    ticket_icon = HoverAnimatedIcon(
                        "animated.ticket", 18, frame_interval_ms=41,
                        autoplay=True, mouse_transparent=True,
                    )
                    ticket_icon.setObjectName("animatedWatchMetadataIcon")
                    caption_icon.addWidget(platform_icon)
                    caption_icon.addWidget(ticket_icon)
                    self.platform_icon_stack = caption_icon
                else:
                    icon_id, category, variant = meta_icons[key]
                    caption_icon = QLabel(); caption_icon.setFixedSize(18, 18)
                    caption_icon.setPixmap(
                        IconProvider.pixmap(icon_id, 16, "#C8D0D8")
                        if category == "semantic"
                        else IconRegistry.pixmap(icon_id, 16, variant=variant, category=category)
                    )
                caption_row.addWidget(caption_icon)
            caption_row.addWidget(caption); caption_row.addStretch(1)
            box = QVBoxLayout(); box.addLayout(caption_row); box.addWidget(value); self.metadata.addLayout(box, row, column); self.meta_values[key] = value; self.meta_captions[key] = caption
        info.addLayout(self.metadata)
        self.description = QLabel(); self.description.setWordWrap(True); self.description.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.description.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self.description.setStyleSheet("font-size:11pt; line-height:1.4; color:#CAD1D7;"); info.addWidget(self.description)
        hero.addLayout(info, 1); self.root.addLayout(hero)

        self.content_tabs = QTabWidget()
        self.content_tabs.setObjectName("gameDetailTabs")
        self.content_tabs.setStyleSheet(
            "QTabWidget::pane{border:0;background:transparent;}"
            "QTabBar::tab{background:transparent;border:0;border-bottom:2px solid "
            "transparent;padding:10px 24px;color:#AEB8C2;}"
            f"QTabBar::tab:selected{{color:white;border-bottom-color:{ACCENT};}}"
            f"QTabBar::tab:hover{{color:{ACCENT};}}"
        )
        self.about_page = QWidget()
        self.about_page.setStyleSheet("background:transparent;")
        self.about_layout = QVBoxLayout(self.about_page)
        self.about_layout.setContentsMargins(0, 12, 0, 0)
        self.about_layout.setSpacing(18)
        self.journey_tab = QWidget()
        self.journey_tab.setStyleSheet("background:transparent;")
        self.journey_layout = QVBoxLayout(self.journey_tab)
        self.journey_layout.setContentsMargins(0, 8, 0, 0)
        self.journey_layout.setSpacing(0)
        self.content_tabs.addTab(self.about_page, "ОБ ИГРЕ")
        self.content_tabs.addTab(self.journey_tab, "JOURNEY")
        self.content_tabs.currentChanged.connect(self._apply_responsive_profile)
        self.root.addWidget(self.content_tabs)
        # Surplus viewport height belongs to the tab content, never the hero.
        # This makes header geometry independent from catalog completeness.
        self.root.setStretch(self.root.indexOf(self.content_tabs), 1)

        self.tags_widget = QFrame()
        self.tags_widget.setObjectName("tagGroups")
        self.tags_widget.setStyleSheet(
            "QFrame#tagGroups{background:#081118;border:1px solid #26343E;"
            "border-radius:7px;}"
        )
        tags_root = QVBoxLayout(self.tags_widget)
        tags_root.setContentsMargins(14, 12, 14, 12)
        self.official_tags_title = QLabel("ОФИЦИАЛЬНЫЕ ТЕГИ")
        self.official_tags_title.setObjectName("caption")
        tags_root.addWidget(self.official_tags_title)
        self.official_tags_grid = QGridLayout()
        tags_root.addLayout(self.official_tags_grid)
        personal_heading = QHBoxLayout()
        personal_title = QLabel("МОИ ТЕГИ")
        personal_title.setObjectName("caption")
        personal_heading.addWidget(personal_title)
        personal_heading.addStretch()
        self.tags_button = QPushButton("ДОБАВИТЬ ТЕГ")
        self.tags_button.clicked.connect(self._edit_tags)
        personal_heading.addWidget(self.tags_button)
        tags_root.addLayout(personal_heading)
        self.personal_tags_grid = QGridLayout()
        tags_root.addLayout(self.personal_tags_grid)
        self.about_layout.addWidget(self.tags_widget)

        from app.ui.game_detail.doom_aw02_panel import DoomAw02Panel
        self.aw02_panel = DoomAw02Panel()
        self.aw02_panel.changed.connect(self.aw02_changed.emit)
        self.journey_layout.addWidget(self.aw02_panel, 1)

        self.official_title = QLabel("ОФИЦИАЛЬНЫЕ СВЕДЕНИЯ")
        self.official_title.setStyleSheet("font-size:15pt; font-weight:600;")
        self.about_layout.addWidget(self.official_title)
        self.official_details = QGridLayout(); self.official_details.setSpacing(12)
        self.about_layout.addLayout(self.official_details)
        self.requirements_panel = SystemRequirementsPanel()
        self.chronology_panel = ChronologyPanel()
        self.chronology_panel.catalog_item_requested.connect(self.catalog_item_requested.emit)

        ratings_title = QLabel("ОЦЕНКИ И ИСТОЧНИКИ"); ratings_title.setStyleSheet("font-size:15pt; font-weight:600;"); self.about_layout.addWidget(ratings_title)
        ratings = QHBoxLayout(); ratings.setSpacing(12)
        self.general_card, self.general_value = self._score_card("СРЕДНЯЯ ОЦЕНКА", "VELORA", SUCCESS); ratings.addWidget(self.general_card)
        self.personal_card, self.personal_value = self._score_card("МОЯ ОЦЕНКА", "ЛИЧНАЯ", WARNING); ratings.addWidget(self.personal_card)
        self.critic_values = {}
        self.source_cards = []
        initial_sources = ("Metacritic", "IGN", "DualShockers", "PC Gamer")
        for source in initial_sources:
            color = source_brand_color(source)
            card, value = self._score_card(source.upper(), source, color); self.critic_values[source] = value; self.source_cards.append((card, value)); ratings.addWidget(card)
        self.about_layout.addLayout(ratings)

        lower = QHBoxLayout(); lower.setSpacing(14)
        self.stats = self._panel("МОЯ СТАТИСТИКА"); self.stats_text = QLabel(); self.stats_text.setWordWrap(True); self.stats.layout().addWidget(self.stats_text); lower.addWidget(self.stats, 1)
        self.criteria = self._panel("КРИТЕРИИ МОЕЙ ОЦЕНКИ"); self.criteria_text = QLabel(); self.criteria_text.setWordWrap(True); self.criteria.layout().addWidget(self.criteria_text); lower.addWidget(self.criteria, 1)
        self.activity = self._panel("ИСТОРИЯ ИЗМЕНЕНИЙ"); self.activity_text = QLabel(); self.activity_text.setWordWrap(True); self.activity.layout().addWidget(self.activity_text); lower.addWidget(self.activity, 1)
        self.about_layout.addLayout(lower)
        self.about_layout.addWidget(self.requirements_panel)
        self.about_layout.addWidget(self.chronology_panel)
        self.about_layout.addStretch()
        self.setWidget(content)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_responsive_profile()

    def _apply_responsive_profile(self, *_args) -> None:
        """Keep the complete Journey visible in the common Full HD viewport."""
        if not hasattr(self, "content_tabs"):
            return
        journey_active = self.content_tabs.currentIndex() == 1
        viewport_height = self.viewport().height()
        small = journey_active and viewport_height <= 900
        compact = journey_active and 900 < viewport_height <= 1080
        self.setProperty(
            "journeyResponsiveProfile",
            "small" if small else "fullhd" if compact else "expanded",
        )
        if small or compact:
            self.root.setContentsMargins(18, 10, 18, 16)
            self.root.setSpacing(10)
            self.hero_layout.setSpacing(18)
            if small:
                self.cover.setFixedSize(140, 210)
            else:
                self.cover.setFixedSize(170, 255)
            self.description.setMaximumHeight(40 if small else 58)
            self.metadata.setVerticalSpacing(5 if small else 7)
            self.metadata.setHorizontalSpacing(28)
            self.journey_layout.setContentsMargins(0, 4, 0, 0)
            self.content_tabs.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred if small else QSizePolicy.Policy.Ignored,
            )
            self.content_tabs.setMinimumHeight(673 if small else 711)
            # QScrollArea otherwise honours the large preferred size reported
            # by the horizontally scrollable Timeline and enlarges the whole
            # page beyond a Full HD viewport.  In the Journey profile the
            # viewport is authoritative; Timeline keeps its own horizontal
            # navigation while the page itself stays scrollbar-free.
        else:
            self.root.setContentsMargins(24, 18, 24, 28)
            self.root.setSpacing(18)
            self.hero_layout.setSpacing(22)
            self.cover.setFixedSize(210, 315)
            self.description.setMaximumHeight(16777215)
            self.metadata.setVerticalSpacing(12)
            self.metadata.setHorizontalSpacing(34)
            self.journey_layout.setContentsMargins(0, 8, 0, 0)
            self.content_tabs.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.content_tabs.setMinimumHeight(0)
        if journey_active:
            self._content.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred if small else QSizePolicy.Policy.Ignored,
            )
            self._content.setMaximumSize(
                max(0, self.viewport().width()),
                16777215 if small else max(0, self.viewport().height()),
            )
        else:
            self._content.setMaximumSize(16777215, 16777215)
            self._content.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        self._content.updateGeometry()

    def _edit_tags(self) -> None:
        if not self.game or self.tag_presenter is None:
            return
        from app.ui.dialogs.tag_editor_dialog import TagEditorDialog
        dialog = TagEditorDialog(list(self.game.tags), self)
        if dialog.exec():
            state = self.tag_presenter.save_personal(
                self._contracts_catalog_id(self.game), dialog.tags()
            )
            self.game.tags = list(state.personal)
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
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        heading_row = QHBoxLayout(); heading_row.setContentsMargins(0, 0, 0, 0)
        icon_map = {
            "БЮДЖЕТ": ("film_budget", "media", "dark"), "СТРАНА": ("globe", "ui", "dark"),
            "ЯЗЫКИ ИНТЕРФЕЙСА": ("globe", "ui", "dark"), "НАГРАДЫ": ("trophy", "achievements", "dark"),
            "DLC": ("metadata.dlc", "semantic", "dark"), "СИСТЕМНЫЕ": ("metadata.system", "semantic", "dark"),
            "ИСХОДНЫЙ": ("code_display", "ui", "svg"), "АРХИТЕКТУРЫ": ("ai_chip", "hardware", "dark"),
            "ЯЗЫКИ РАЗРАБОТКИ": ("python", "brands", "svg"), "ДВИЖОК": ("metadata.engine", "semantic", "dark"),
            "РАСПРОСТРАНЕНИЕ": ("announcement", "marketing", "dark"),
            "МАГАЗИНЫ": ("storefront", "stores", "svg"),
        }
        match = next((value for prefix, value in icon_map.items() if title.startswith(prefix)), None)
        if match:
            icon_id, category, variant = match
            if icon_id == "film_budget":
                icon = HoverAnimatedIcon("animated.budget", 18)
            else:
                icon = QLabel(); icon.setFixedSize(18, 18)
                icon.setPixmap(
                    IconProvider.pixmap(icon_id, 16, "#C8D0D8")
                    if category == "semantic"
                    else IconRegistry.pixmap(icon_id, 16, variant=variant, category=category)
                )
            heading_row.addWidget(icon)
        heading = QLabel(title); heading.setObjectName("caption"); heading_row.addWidget(heading); heading_row.addStretch(); layout.addLayout(heading_row); return panel

    def set_game(self, game: GameData) -> None:
        if self._status_menu_media_type != game.media_type:
            self.status_badge.set_media_type(game.media_type)
            self._status_menu_media_type = game.media_type
        self.game = game; self.title.setText(game.title); self.route.setText(f"{game.category}  •  {game.subgroup or 'Без подгруппы'}"); self._render_tags(game)
        is_aw02_doom = game.catalog_id == "g-shooter-fps-002"
        is_game = game.media_type == "Игры"
        self.aw02_panel.setVisible(is_aw02_doom)
        if not is_game and self.content_tabs.currentIndex() == 1:
            self.content_tabs.setCurrentIndex(0)
        self.content_tabs.setTabVisible(1, is_game)
        self.content_tabs.setTabEnabled(1, is_game)
        if is_aw02_doom:
            self.aw02_panel.refresh()
        self.breadcrumb.setText(f"{game.media_type.upper()}  /  {game.category.upper()}  /  {(game.subgroup or 'КАРТОЧКА').upper()}")
        developer_text, developer_tooltip = compact_entities(game.developer)
        publisher_text, publisher_tooltip = compact_entities(game.publisher)
        # CompanyLogoRow needs the original entity list to resolve the primary
        # reviewed company and calculate +N. Compact text is tooltip-only.
        values = {
            "Разработчик": game.developer,
            "Издатель": game.publisher,
            "Год выхода": game.year,
            "Платформы": game.platform,
            "Количество игроков": game.mode,
            "Возраст": game.age_rating,
        }
        labels = {
            "Игры": ("РАЗРАБОТЧИК", "ИЗДАТЕЛЬ", "ПЛАТФОРМЫ", "КОЛИЧЕСТВО ИГРОКОВ"),
            "Фильмы": ("РЕЖИССЁР", "СТУДИЯ", "ГДЕ СМОТРЕТЬ", "ДЛИТЕЛЬНОСТЬ"),
            "Сериалы": ("СОЗДАТЕЛЬ", "СТУДИЯ", "ГДЕ СМОТРЕТЬ", "КОЛИЧЕСТВО СЕЗОНОВ"),
            "Программы": ("РАЗРАБОТЧИК", "ИЗДАТЕЛЬ", "ПЛАТФОРМЫ", "ТИП"),
        }.get(game.media_type, ("СОЗДАТЕЛЬ", "ИЗДАТЕЛЬ", "ПЛАТФОРМА", "ФОРМАТ"))
        for key, text in zip(("Разработчик","Издатель","Платформы","Количество игроков"), labels): self.meta_captions[key].setText(text)
        self.studio_icon_stack.setCurrentIndex(
            1 if game.media_type in ("Фильмы", "Сериалы") else 0
        )
        self.platform_icon_stack.setCurrentIndex(
            1 if game.media_type in ("Фильмы", "Сериалы") else 0
        )
        for key, value in values.items(): self.meta_values[key].setText(value or "—")
        self.meta_values["Разработчик"].setToolTip(developer_tooltip)
        self.meta_values["Издатель"].setToolTip(publisher_tooltip)
        description = (
            DOOM_ETERNAL_REFERENCE_DESCRIPTION
            if is_aw02_doom
            else game.description
        )
        self.description.setText(
            description
            or "Описание для этого объекта пока не добавлено в Velora Studio."
        )
        self._fill_official_details(game)
        self.chronology_panel.set_chronology(
            game.franchise_name, game.chronology, game.catalog_id
        )
        self.general_value.setText(self._score(game.general_score))
        self.personal_value.setText(self._score(game.personal_score))
        general_color = rating_color(game.general_score)
        personal_color = rating_color(game.personal_score)
        self.general_value.setStyleSheet(
            f"color:{general_color}; font-size:25pt; font-weight:700; border:0;"
        )
        self.personal_value.setStyleSheet(
            f"color:{personal_color}; font-size:25pt; font-weight:700; border:0;"
        )
        general_labels = self.general_card.findChildren(QLabel)
        if general_labels:
            general_labels[0].setStyleSheet(
                f"color:{general_color}; font-size:10pt; font-weight:800; border:0;"
            )
        personal_labels = self.personal_card.findChildren(QLabel)
        if personal_labels:
            personal_labels[0].setStyleSheet(
                f"color:{personal_color}; font-size:10pt; font-weight:800; border:0;"
            )
        self.rate_button.setText("ИЗМЕНИТЬ ОЦЕНКУ" if game.personal_score != "—" else "ОЦЕНИТЬ")
        self.status_badge.set_status(game.status)
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
        self.favorite.setText("В ИЗБРАННОМ" if game.favorite else "В ИЗБРАННОЕ")
        apply_favorite_icon(self.favorite, game.favorite, size=20)
        self._set_cover(game.cover_path)

    def refresh_aw02(self) -> None:
        if self.game is not None and self.game.catalog_id == "g-shooter-fps-002":
            self.aw02_panel.refresh()

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
        if game.media_type == "Игры" and game.engine:
            technical_value = game.engine
            if game.anti_cheat:
                technical_value += f"\n\nАНТИЧИТ\n{game.anti_cheat}"
            entries.append(("ДВИЖОК", technical_value))
        elif game.media_type != "Игры" and game.distribution_model:
            entries.append(("РАСПРОСТРАНЕНИЕ", game.distribution_model))
        if game.stores: entries.append(("МАГАЗИНЫ", ", ".join(game.stores)))
        self.official_title.setVisible(bool(entries))
        for index,(title,text) in enumerate(entries):
            panel=self._panel(title)
            anti_cheat_value = ""
            if title == "ДВИЖОК" and "\n\nАНТИЧИТ\n" in text:
                text, anti_cheat_value = text.split("\n\nАНТИЧИТ\n", 1)
            value=QLabel(text); value.setWordWrap(True); value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            value.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
            )
            value.setStyleSheet("color:#CAD1D7; border:0; line-height:1.35;")
            if title == "ДВИЖОК":
                panel.layout().addWidget(value)
                if anti_cheat_value:
                    anti_heading = QHBoxLayout()
                    anti_heading.setContentsMargins(0, 5, 0, 0)
                    anti_icon = QLabel(); anti_icon.setFixedSize(18, 18)
                    anti_icon.setPixmap(IconRegistry.pixmap("anti_cheat", 16, variant="dark", category="details"))
                    anti_caption = QLabel("АНТИЧИТ"); anti_caption.setObjectName("caption")
                    anti_heading.addWidget(anti_icon); anti_heading.addWidget(anti_caption); anti_heading.addStretch(1)
                    panel.layout().addLayout(anti_heading)
                    anti_value = QLabel(anti_cheat_value)
                    anti_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    anti_value.setStyleSheet("color:#CAD1D7; border:0;")
                    panel.layout().addWidget(anti_value)
            elif title == "DLC":
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
        official = list(game.system_tags)
        personal = list(game.tags)
        if self.tag_presenter is not None:
            try:
                stored = self.tag_presenter.load(self._contracts_catalog_id(game))
                official = list(stored.official) or official
                personal = list(stored.personal)
                game.tags = personal
            except Exception:
                pass
        self._fill_tag_grid(self.official_tags_grid, official, False)
        self._fill_tag_grid(self.personal_tags_grid, personal, True)
        self.official_tags_title.setVisible(bool(official))
        self.tags_button.setText("ИЗМЕНИТЬ ТЕГИ" if personal else "ДОБАВИТЬ ТЕГ")

    def _fill_tag_grid(
        self, layout: QGridLayout, tags: list[str], personal: bool,
    ) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index, tag in enumerate(tags):
            chip = QPushButton(f"#{tag}")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip(
                "Личный тег" if personal else "Тег официального каталога"
            )
            chip.setStyleSheet(
                "QPushButton{color:#D3D9DF;background:#0A1118;"
                "border:1px solid #34434E;border-radius:5px;padding:5px 10px;}"
                f"QPushButton:hover{{border-color:{ACCENT};color:white;}}"
                f"QPushButton:checked{{border-color:{ACCENT};color:#E7CEFF;"
                "background:#1A0E29;}}"
            )
            chip.clicked.connect(
                lambda checked=False, value=tag:
                self.tag_filter_requested.emit(value)
            )
            layout.addWidget(chip, index // 8, index % 8)
        layout.setColumnStretch(8, 1)

    @staticmethod
    def _contracts_catalog_id(game: GameData) -> str:
        if game.catalog_id == "g-shooter-fps-002":
            from app.application.doom_vertical_slice import DOOM_ETERNAL_ID
            return DOOM_ETERNAL_ID
        return game.catalog_id

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
        self.game.favorite = not self.game.favorite
        selected = self.game.favorite
        self.favorite.setText("В ИЗБРАННОМ" if selected else "В ИЗБРАННОЕ")
        if self._favorite_animation is not None:
            self._favorite_animation.stop()
        self._favorite_animation = animate_icon_pulse(
            self.favorite,
            adding=selected,
            state_change=lambda: apply_favorite_icon(self.favorite, selected, size=20),
        )
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
        self.status_badge.set_status(status)

    @staticmethod
    def _score(value: str) -> str:
        try: return f"{float(value):.1f}"
        except ValueError: return "—"
