from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "data" / "catalog.db"
BACKUP = ROOT / "data" / "catalog.before_aw010_critic_slots.db"

SOURCE_SETS = {
    "Игры": ("Metacritic", "IGN", "DualShockers", "PC Gamer"),
    "Фильмы": ("IMDb", "Кинопоиск", "Rotten Tomatoes", "Metacritic"),
    "Сериалы": ("IMDb", "Кинопоиск", "Rotten Tomatoes", "Metacritic"),
    "Программы": ("PCMag", "TechRadar", "CNET", "Tom's Guide"),
}


def main() -> None:
    if not BACKUP.exists():
        shutil.copy2(CATALOG, BACKUP)
    connection = sqlite3.connect(CATALOG)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT catalog_id,media_type,critic_scores_json FROM catalog_items"
        ).fetchall()
        connection.execute("BEGIN IMMEDIATE")
        updated = 0
        for row in rows:
            try:
                stored = json.loads(row["critic_scores_json"] or "{}")
            except (json.JSONDecodeError, TypeError):
                stored = {}
            if not isinstance(stored, dict):
                stored = {}
            ordered: dict[str, float | None] = {}
            for source in SOURCE_SETS.get(row["media_type"], ()):
                ordered[source] = stored.get(source)
            for source, value in stored.items():
                if source not in ordered:
                    ordered[source] = value
            available = [
                float(value)
                for value in ordered.values()
                if value is not None
            ]
            general_score = round(sum(available) / len(available), 1) if available else 0.0
            connection.execute(
                "UPDATE catalog_items SET critic_scores_json=?,general_score=?,"
                "primary_critic_source='' WHERE catalog_id=?",
                (json.dumps(ordered, ensure_ascii=False), general_score, row["catalog_id"]),
            )
            updated += 1
        connection.commit()
        print(f"Нормализовано карточек: {updated}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
