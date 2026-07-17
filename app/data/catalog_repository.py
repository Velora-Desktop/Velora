from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models.game import GameData, default_status


CATALOG_DB = Path(__file__).resolve().parents[2] / "data" / "catalog.db"


def normalize_requirements(values: dict[str, str]) -> dict[str, str]:
    normalized = dict(values or {})
    for legacy, minimum in (("os", "os_min"), ("cpu", "cpu_min"), ("gpu", "gpu_min"), ("ram", "ram_min"), ("storage", "storage_min")):
        if normalized.get(legacy) and not normalized.get(minimum):
            normalized[minimum] = normalized[legacy]
    return normalized
MEDIA_TYPES = ("Игры", "Фильмы", "Сериалы", "Программы")


def load_catalog_items() -> list[GameData]:
    """Load every official media item from the Studio-published catalog."""
    if not CATALOG_DB.exists():
        return []
    connection = sqlite3.connect(f"file:{CATALOG_DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(catalog_items)")}
        rows = connection.execute(
            "SELECT * FROM catalog_items WHERE is_active=1 ORDER BY media_type,category,subgroup,title"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        connection.close()

    def value(row: sqlite3.Row, name: str, fallback=None):
        return row[name] if name in columns and row[name] is not None else fallback

    def json_value(row: sqlite3.Row, name: str, fallback):
        try: return json.loads(value(row, name, json.dumps(fallback)))
        except (json.JSONDecodeError, TypeError): return fallback

    items: list[GameData] = []
    for row in rows:
        media_type = row["media_type"]
        availability = value(row, "availability", "")
        duration = value(row, "duration_minutes")
        seasons = value(row, "seasons")
        platforms = value(row, "platforms", "")
        player_modes = value(row, "player_modes", "")
        if media_type in ("Фильмы", "Сериалы"):
            platform = availability
        else:
            platform = platforms
        if media_type == "Фильмы":
            mode = f"{duration} мин" if duration else "—"
        elif media_type == "Сериалы":
            mode = f"{seasons} сез." if seasons else "—"
        else:
            mode = player_modes or ("ПО" if media_type == "Программы" else "—")

        try:
            critics = json.loads(value(row, "critic_scores_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            critics = {}
        if not critics:
            critics = {
                "Metacritic": value(row, "metacritic_score"),
                "IGN": value(row, "ign_score"),
                "DualShockers": value(row, "dualshockers_score"),
                "PC Gamer": value(row, "pc_gamer_score"),
            }
        items.append(GameData(
            title=row["title"], general_score=f'{row["general_score"]:.1f}', personal_score="—",
            status=default_status(media_type), developer=value(row, "developer", "—"),
            year=str(value(row, "release_year", "—")), platform=platform or "—", mode=mode,
            description=value(row, "description", ""), publisher=value(row, "publisher", "—"),
            release_year=str(value(row, "release_year", "—")), age_rating=int(row["age_rating"]),
            catalog_id=row["catalog_id"], category=row["category"], subgroup=row["subgroup"],
            cover_path=value(row, "cover_path", ""), critic_scores=critics, media_type=media_type,
            duration_minutes=duration, seasons=seasons, availability=availability,
            publisher_countries=json_value(row,"publisher_countries_json",[]),
            interface_languages=json_value(row,"interface_languages_json",[]),
            system_requirements=normalize_requirements(json_value(row,"system_requirements_json",{})),
            awards=json_value(row,"awards_json",[]), dlc=json_value(row,"dlc_json",[]),
            cast=json_value(row,"cast_json",[]), source_code_type=value(row,"source_code_type",""),
            architectures=json_value(row,"architectures_json",[]),
            programming_languages=json_value(row,"programming_languages_json",[]),
            distribution_model=value(row,"distribution_model",""), stores=json_value(row,"stores_json",[]),
            budget_amount=value(row,"budget_amount"), budget_currency=value(row,"budget_currency",""),
        ))
    return items


def catalog_categories(items: list[GameData], media_type: str) -> dict[str, int]:
    categories: dict[str, int] = {}
    for item in items:
        if item.media_type == media_type:
            categories[item.category.upper()] = categories.get(item.category.upper(), 0) + 1
    screen_genres = (
        "ДРАМА", "ФАНТАСТИКА", "БОЕВИК", "ДЕТЕКТИВ",
        "КОМЕДИЯ", "АНИМАЦИЯ", "УЖАСЫ", "ФЭНТЕЗИ",
    )
    preferred = {
        "Игры": ("ШУТЕРЫ", "RPG", "ГОНКИ", "СТРАТЕГИИ"),
        "Фильмы": screen_genres,
        "Сериалы": screen_genres,
        "Программы": ("ОПЕРАЦИОННЫЕ СИСТЕМЫ", "СИСТЕМНЫЕ", "ОФИСНЫЕ", "ГРАФИКА", "РАЗРАБОТКА"),
    }.get(media_type, ())
    order = {name: index for index, name in enumerate(preferred)}
    return dict(sorted(categories.items(), key=lambda pair: (order.get(pair[0], 999), pair[0])))


def media_groups(items: list[GameData], media_type: str, category: str) -> dict[str, tuple[GameData, ...]]:
    groups: dict[str, list[GameData]] = {}
    for item in items:
        if item.media_type == media_type and item.category.upper() == category.upper():
            groups.setdefault(item.subgroup.upper(), []).append(item)
    return {name: tuple(values) for name, values in groups.items()}


def load_game_groups(category: str = "ШУТЕРЫ") -> dict[str, tuple[GameData, ...]]:
    """Backward-compatible facade used by older catalog code."""
    return media_groups(load_catalog_items(), "Игры", category)
