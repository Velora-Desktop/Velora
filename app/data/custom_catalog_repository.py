from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.models.game import GameData, default_status


class CustomCatalogRepository:
    """Local, user-owned catalog. It never writes to the official catalog.db."""

    def __init__(self, database_path: Path) -> None:
        self.path = Path(database_path)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _slug(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9а-яё]+", "-", value.casefold(), flags=re.IGNORECASE).strip("-")
        return normalized or "item"

    def sections(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT s.id,s.name,s.position,COUNT(i.catalog_id) AS item_count "
                "FROM custom_sections s LEFT JOIN custom_catalog_items i ON i.section_id=s.id AND i.deleted_at IS NULL "
                "GROUP BY s.id ORDER BY s.position,s.name COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_section(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Название раздела не заполнено.")
        now = self._now()
        with self._connection() as connection:
            row = connection.execute("SELECT id FROM custom_sections WHERE name=? COLLATE NOCASE", (name,)).fetchone()
            if row:
                return int(row[0])
            position = connection.execute("SELECT COALESCE(MAX(position),0)+1 FROM custom_sections").fetchone()[0]
            return int(connection.execute(
                "INSERT INTO custom_sections(name,position,created_at,updated_at) VALUES(?,?,?,?)",
                (name, position, now, now),
            ).lastrowid)

    def delete_section(self, name: str) -> bool:
        """Delete one user-owned section and all of its local branches/cards."""
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM custom_sections WHERE name=? COLLATE NOCASE",
                (name.strip(),),
            )
        return cursor.rowcount > 0

    def rename_section(self, old_name: str, new_name: str) -> bool:
        """Rename a user-owned section without changing its local cards or IDs."""
        old_name, new_name = old_name.strip(), new_name.strip()
        if not old_name or not new_name:
            raise ValueError("Выберите раздел и укажите новое название.")
        now = self._now()
        with self._connection() as connection:
            duplicate = connection.execute(
                "SELECT id FROM custom_sections WHERE name=? COLLATE NOCASE",
                (new_name,),
            ).fetchone()
            current = connection.execute(
                "SELECT id FROM custom_sections WHERE name=? COLLATE NOCASE",
                (old_name,),
            ).fetchone()
            if current is None:
                return False
            if duplicate is not None and int(duplicate[0]) != int(current[0]):
                raise ValueError(f"Раздел «{new_name}» уже существует.")
            cursor = connection.execute(
                "UPDATE custom_sections SET name=?,updated_at=? WHERE id=?",
                (new_name, now, int(current[0])),
            )
        return cursor.rowcount > 0

    def branches(self, section: str) -> list[dict]:
        """Return stored and card-derived category/subcategory pairs."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT category, subgroup, MIN(position) AS position
                FROM (
                    SELECT b.category, b.subgroup, b.position
                    FROM custom_catalog_branches b
                    JOIN custom_sections s ON s.id=b.section_id
                    WHERE s.name=? COLLATE NOCASE
                    UNION ALL
                    SELECT i.category, i.subgroup, 100000
                    FROM custom_catalog_items i
                    JOIN custom_sections s ON s.id=i.section_id
                    WHERE s.name=? COLLATE NOCASE AND i.deleted_at IS NULL
                )
                GROUP BY category, subgroup
                ORDER BY position, category COLLATE NOCASE, subgroup COLLATE NOCASE
                """,
                (section.strip(), section.strip()),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_branch(self, section: str, category: str, subgroup: str) -> int:
        values = (section.strip(), category.strip(), subgroup.strip())
        if not all(values):
            raise ValueError("Заполните раздел, категорию и подкатегорию.")
        section_id = self.save_section(values[0])
        now = self._now()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM custom_catalog_branches "
                "WHERE section_id=? AND category=? COLLATE NOCASE AND subgroup=? COLLATE NOCASE",
                (section_id, values[1], values[2]),
            ).fetchone()
            if row:
                return int(row[0])
            position = connection.execute(
                "SELECT COALESCE(MAX(position),0)+1 FROM custom_catalog_branches WHERE section_id=?",
                (section_id,),
            ).fetchone()[0]
            return int(connection.execute(
                "INSERT INTO custom_catalog_branches(section_id,category,subgroup,position,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (section_id, values[1], values[2], position, now, now),
            ).lastrowid)

    def save_item(self, section: str, category: str, subgroup: str, title: str,
                  description: str = "", creator: str = "", release_year: int | None = None,
                  age_rating: int = 0, cover_path: str = "") -> str:
        values = [section.strip(), category.strip(), subgroup.strip(), title.strip()]
        if not all(values):
            raise ValueError("Заполните раздел, категорию, подкатегорию и название объекта.")
        section_id = self.save_section(values[0])
        self.save_branch(values[0], values[1], values[2])
        prefix = f"u-{self._slug(values[0])}-{self._slug(values[1])}-{self._slug(values[2])}"
        now = self._now()
        with self._connection() as connection:
            number = connection.execute(
                "SELECT COUNT(*)+1 FROM custom_catalog_items WHERE catalog_id LIKE ?", (prefix + "-%",)
            ).fetchone()[0]
            catalog_id = f"{prefix}-{number:03d}"
            connection.execute(
                "INSERT INTO custom_catalog_items(catalog_id,section_id,category,subgroup,title,description,creator,release_year,cover_path,age_rating,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (catalog_id, section_id, values[1], values[2], values[3], description.strip(), creator.strip(),
                 release_year, cover_path.strip(), max(0, min(21, int(age_rating))), now, now),
            )
        return catalog_id

    def items(self) -> list[GameData]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT i.*,s.name AS section_name FROM custom_catalog_items i "
                "JOIN custom_sections s ON s.id=i.section_id WHERE i.deleted_at IS NULL "
                "ORDER BY s.position,i.category,i.subgroup,i.title"
            ).fetchall()
        return [GameData(
            title=row["title"], general_score="—", personal_score="—",
            status=default_status(row["section_name"]), developer=row["creator"] or "—",
            year=str(row["release_year"] or "—"), platform="—", mode="—",
            description=row["description"] or f"Пользовательский объект «{row['title']}».",
            publisher="—", release_year=str(row["release_year"] or "—"),
            age_rating=int(row["age_rating"] or 0), catalog_id=row["catalog_id"],
            category=row["category"], subgroup=row["subgroup"], cover_path=row["cover_path"],
            media_type=row["section_name"], source_type="custom",
        ) for row in rows]
