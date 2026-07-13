from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


USER_DB = Path.home() / "AppData" / "Local" / "Velora" / "user.db"


@dataclass(slots=True)
class LocalProfile:
    display_name: str = "Пользователь"
    bio: str = "Моя локальная библиотека Velora"
    avatar_path: str = ""


class UserRepository:
    def __init__(self, path: Path = USER_DB) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS local_profile (
                    profile_id INTEGER PRIMARY KEY CHECK(profile_id = 1),
                    display_name TEXT NOT NULL,
                    bio TEXT NOT NULL DEFAULT '',
                    avatar_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_game_state (
                    catalog_id TEXT PRIMARY KEY,
                    personal_score REAL,
                    status TEXT,
                    playtime_hours REAL NOT NULL DEFAULT 0,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    rating_criteria_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                );
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(user_game_state)")}
            if "hidden" not in columns:
                connection.execute("ALTER TABLE user_game_state ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0")
            now = datetime.now(timezone.utc).isoformat()
            connection.execute("INSERT OR IGNORE INTO local_profile VALUES(1, ?, ?, '', ?, ?)", ("Пользователь", "Моя локальная библиотека Velora", now, now))
            connection.commit()
        finally:
            connection.close()

    def load_profile(self) -> LocalProfile:
        connection = sqlite3.connect(self.path)
        try: row = connection.execute("SELECT display_name, bio, avatar_path FROM local_profile WHERE profile_id=1").fetchone()
        finally: connection.close()
        return LocalProfile(*row)

    def save_profile(self, profile: LocalProfile) -> None:
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("UPDATE local_profile SET display_name=?, bio=?, avatar_path=?, updated_at=? WHERE profile_id=1", (profile.display_name, profile.bio, profile.avatar_path, datetime.now(timezone.utc).isoformat()))
            connection.commit()
        finally: connection.close()

    def apply_game_states(self, games) -> None:
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row
        try: states = {row["catalog_id"]: row for row in connection.execute("SELECT * FROM user_game_state")}
        finally: connection.close()
        for game in games:
            state = states.get(game.catalog_id)
            if state is None: continue
            game.personal_score = "—" if state["personal_score"] is None else f'{state["personal_score"]:.1f}'
            game.status = state["status"] or "НЕ НАЧИНАЛ"
            game.playtime = "—" if not state["playtime_hours"] else f'{state["playtime_hours"]:g} ч'
            game.favorite = bool(state["favorite"])
            game.rating_criteria = json.loads(state["rating_criteria_json"] or "{}")
            game.hidden = bool(state["hidden"])

    def save_game_state(self, game) -> None:
        try: personal_score = float(game.personal_score)
        except ValueError: personal_score = None
        try: playtime = float(game.playtime.replace("ч", "").strip().replace(",", "."))
        except ValueError: playtime = 0.0
        if not game.catalog_id: return
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("""
                INSERT INTO user_game_state(catalog_id, personal_score, status, playtime_hours, favorite, rating_criteria_json, updated_at, hidden)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(catalog_id) DO UPDATE SET personal_score=excluded.personal_score,
                    status=excluded.status, playtime_hours=excluded.playtime_hours,
                    favorite=excluded.favorite, rating_criteria_json=excluded.rating_criteria_json,
                    updated_at=excluded.updated_at, hidden=excluded.hidden
            """, (game.catalog_id, personal_score, game.status, playtime, int(game.favorite), json.dumps(game.rating_criteria, ensure_ascii=False), datetime.now(timezone.utc).isoformat(), int(game.hidden)))
            connection.commit()
        finally: connection.close()
