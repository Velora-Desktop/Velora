from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models.game import GameData


CATALOG_DB = Path(__file__).resolve().parents[2] / "data" / "catalog.db"


def load_game_groups(category: str = "Шутеры") -> dict[str, tuple[GameData, ...]]:
    """Load official cards and route them using category/subgroup from Studio."""
    if not CATALOG_DB.exists():
        return {}
    connection = sqlite3.connect(f"file:{CATALOG_DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT catalog_id, title, subgroup, age_rating, general_score,
                   metacritic_score, ign_score, dualshockers_score, pc_gamer_score,
                   developer, publisher, release_year, platforms, player_modes,
                   description, cover_path
            FROM catalog_items
            WHERE media_type = 'Игры' AND category = ? AND is_active = 1
            ORDER BY subgroup, title
            """,
            (category,),
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        connection.close()

    groups: dict[str, list[GameData]] = {}
    for row in rows:
        game = GameData(
            title=row["title"],
            general_score=f'{row["general_score"]:.1f}',
            personal_score="—",
            status="НЕ НАЧИНАЛ",
            developer=row["developer"],
            year=str(row["release_year"] or "—"),
            platform=row["platforms"],
            mode=row["player_modes"],
            description=row["description"],
            publisher=row["publisher"],
            release_year=str(row["release_year"] or "—"),
            age_rating=row["age_rating"],
            catalog_id=row["catalog_id"],
            category=category,
            subgroup=row["subgroup"],
            cover_path=row["cover_path"],
            media_type="Игры",
            critic_scores={
                "Metacritic": row["metacritic_score"], "IGN": row["ign_score"],
                "DualShockers": row["dualshockers_score"], "PC Gamer": row["pc_gamer_score"],
            },
        )
        groups.setdefault(row["subgroup"].upper(), []).append(game)
    return {name: tuple(items) for name, items in groups.items()}
