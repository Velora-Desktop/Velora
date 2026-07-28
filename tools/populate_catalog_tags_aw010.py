from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.db"
BACKUP = ROOT / "data" / "catalog.before_aw010_tags.db"

CATEGORY_TAGS = {
    "Шутеры": ("стрельба", "динамичный бой"),
    "Экшен": ("экшен", "динамичный геймплей"),
    "RPG": ("ролевая игра", "развитие персонажа"),
    "Стратегии": ("стратегия", "тактика"),
    "Гонки": ("гонки", "скорость"),
    "Приключения": ("приключение", "исследование"),
    "Хорроры": ("хоррор", "напряжение"),
    "Симуляторы": ("симулятор", "реализм"),
    "Спортивные": ("спорт", "соревнование"),
    "Файтинги": ("единоборства", "соревнование"),
    "Платформеры": ("платформер", "испытания"),
    "Головоломки": ("головоломки", "логика"),
}

TITLE_TAGS = {
    "doom": ("космос", "демоны"),
    "halo": ("космос", "научная фантастика"),
    "destiny": ("космос", "научная фантастика"),
    "dead space": ("космос", "хоррор"),
    "mass effect": ("космос", "научная фантастика"),
    "starfield": ("космос", "исследование"),
    "outer worlds": ("космос", "научная фантастика"),
    "metro": ("постапокалипсис", "атмосфера"),
    "fallout": ("постапокалипсис", "открытый мир"),
    "last of us": ("постапокалипсис", "драма"),
    "witcher": ("фэнтези", "открытый мир"),
    "elden ring": ("фэнтези", "сложность"),
    "dark souls": ("фэнтези", "сложность"),
    "skyrim": ("фэнтези", "открытый мир"),
    "baldur": ("фэнтези", "партийная игра"),
    "cyberpunk": ("киберпанк", "открытый мир"),
    "bioshock": ("антиутопия", "атмосфера"),
    "red dead": ("вестерн", "открытый мир"),
    "grand theft auto": ("криминал", "открытый мир"),
    "gta": ("криминал", "открытый мир"),
    "max payne": ("нуар", "криминал"),
}


def normalized_tags(title: str, category: str, subgroup: str) -> list[str]:
    values: list[str] = []
    if subgroup:
        values.append(subgroup.casefold())
    values.extend(CATEGORY_TAGS.get(category, (category.casefold(), "интерактивное развлечение")))
    lowered = title.casefold()
    for fragment, tags in TITLE_TAGS.items():
        if fragment in lowered:
            values.extend(tags)
    values.append("одиночная игра")
    result: list[str] = []
    for value in values:
        clean = value.strip()
        if clean and clean.casefold() not in {tag.casefold() for tag in result}:
            result.append(clean)
    return result[:6] if len(result) >= 3 else result + ["игровой процесс"][: 3 - len(result)]


def main() -> None:
    if not BACKUP.exists():
        shutil.copy2(CATALOG, BACKUP)
    connection = sqlite3.connect(CATALOG)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(catalog_items)")}
        if "catalog_tags_json" not in columns:
            connection.execute(
                "ALTER TABLE catalog_items ADD COLUMN catalog_tags_json TEXT NOT NULL DEFAULT '[]'"
            )
        rows = connection.execute(
            "SELECT catalog_id,title,category,subgroup FROM catalog_items "
            "WHERE catalog_id LIKE 'g-%'"
        ).fetchall()
        for catalog_id, title, category, subgroup in rows:
            tags = normalized_tags(title, category, subgroup)
            connection.execute(
                "UPDATE catalog_items SET catalog_tags_json=? WHERE catalog_id=?",
                (json.dumps(tags, ensure_ascii=False), catalog_id),
            )
        connection.commit()
        invalid = connection.execute(
            "SELECT COUNT(*) FROM catalog_items WHERE catalog_id LIKE 'g-%' "
            "AND json_array_length(catalog_tags_json)<3"
        ).fetchone()[0]
        if invalid:
            raise RuntimeError(f"Карточек с недостаточным числом тегов: {invalid}")
        print(f"Обновлено игровых карточек: {len(rows)}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
