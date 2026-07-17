from dataclasses import dataclass, field


MEDIA_STATUSES = {
    "Игры": ("НЕ НАЧИНАЛ", "ПРОХОЖУ", "ПРОШЁЛ", "БРОСИЛ"),
    "Фильмы": ("НЕ СМОТРЕЛ", "СМОТРЮ", "ПОСМОТРЕЛ", "БРОСИЛ"),
    "Сериалы": ("НЕ СМОТРЕЛ", "СМОТРЮ", "ПОСМОТРЕЛ", "ЖДУ НОВЫЙ СЕЗОН", "БРОСИЛ"),
    "Программы": ("НЕ ИСПОЛЬЗОВАЛ", "ИСПОЛЬЗУЮ", "ИСПОЛЬЗОВАЛ", "ОТКАЗАЛСЯ"),
}

GAME_STATUSES = MEDIA_STATUSES["Игры"]


def default_status(media_type: str) -> str:
    return MEDIA_STATUSES.get(media_type, GAME_STATUSES)[0]


@dataclass
class GameData:
    title: str
    general_score: str
    personal_score: str
    status: str
    developer: str
    year: str
    platform: str
    mode: str
    playtime_hours: float = 0.0
    description: str = "Краткая информация об игре появится здесь."
    publisher: str = "—"
    release_year: str = "—"
    history: list[str] = field(default_factory=list)
    rating_criteria: dict[str, int] = field(default_factory=dict)
    favorite: bool = False
    age_rating: int = 0
    catalog_id: str = ""
    category: str = "Шутеры"
    subgroup: str = ""
    cover_path: str = ""
    critic_scores: dict[str, float | None] = field(default_factory=dict)
    media_type: str = "Игры"
    hidden: bool = False
    user_interacted: bool = False
    interaction_started_at: str = ""
    interaction_completed_at: str = ""
    duration_minutes: int | None = None
    seasons: int | None = None
    availability: str = ""
    watch_count: int = 0
    season_number: int = 0
    episode_number: int = 0
    episode_states: dict[str, str] = field(default_factory=dict)
    publisher_countries: list[str] = field(default_factory=list)
    interface_languages: list[str] = field(default_factory=list)
    system_requirements: dict[str, str] = field(default_factory=dict)
    awards: list[str] = field(default_factory=list)
    dlc: list[str] = field(default_factory=list)
    cast: list[dict[str, str]] = field(default_factory=list)
    source_code_type: str = ""
    architectures: list[str] = field(default_factory=list)
    programming_languages: list[str] = field(default_factory=list)
    distribution_model: str = ""
    stores: list[str] = field(default_factory=list)
    budget_amount: float | None = None
    budget_currency: str = ""
