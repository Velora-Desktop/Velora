from dataclasses import dataclass, field


GAME_STATUSES = ("НЕ НАЧИНАЛ", "ПРОХОЖУ", "ПРОШЁЛ", "БРОСИЛ")


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
