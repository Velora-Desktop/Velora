from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.database.migration_runner import MigrationRunner


USER_DB = Path.home() / "AppData" / "Local" / "Velora" / "user.db"
USER_MIGRATIONS = Path(__file__).resolve().parents[1] / "database" / "migrations" / "user"


@dataclass(slots=True)
class LocalProfile:
    display_name: str = "Пользователь"
    bio: str = "Моя локальная библиотека Velora"
    avatar_path: str = ""


class UserRepository:
    def __init__(self, path: Path = USER_DB) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        MigrationRunner(USER_MIGRATIONS).migrate(self.path)
        connection = sqlite3.connect(self.path)
        try:
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
        try:
            states = {row["catalog_id"]: row for row in connection.execute("SELECT * FROM user_game_state")}
            activities: dict[str, list[sqlite3.Row]] = {}
            for row in connection.execute("SELECT * FROM user_activity ORDER BY created_at, id"):
                activities.setdefault(row["catalog_id"], []).append(row)
            episode_states: dict[str, dict[str, str]] = {}
            for row in connection.execute("SELECT catalog_id,season_number,episode_number,state FROM series_episode_state"):
                episode_states.setdefault(row["catalog_id"], {})[f"{row['season_number']}:{row['episode_number']}"] = row["state"]
        finally: connection.close()
        for game in games:
            state = states.get(game.catalog_id)
            if state is None: continue
            game.personal_score = "—" if state["personal_score"] is None else f'{state["personal_score"]:.1f}'
            game.status = state["status"] or game.status
            game.playtime_hours = float(state["playtime_hours"] or 0.0)
            game.favorite = bool(state["favorite"])
            game.rating_criteria = json.loads(state["rating_criteria_json"] or "{}")
            game.hidden = bool(state["hidden"])
            game.watch_count = int(state["watch_count"] or 0)
            game.season_number = int(state["season_number"] or 0)
            game.episode_number = int(state["episode_number"] or 0)
            game.episode_states = episode_states.get(game.catalog_id, {})
            game.user_interacted = True
            game.history = [self._format_activity(row) for row in activities.get(game.catalog_id, [])]

    def save_game_state(self, game) -> None:
        try: personal_score = float(game.personal_score)
        except ValueError: personal_score = None
        playtime = float(game.playtime_hours)
        if not game.catalog_id: return
        game.user_interacted = True
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row
        try:
            previous = connection.execute("SELECT * FROM user_game_state WHERE catalog_id=?", (game.catalog_id,)).fetchone()
            old = {
                "rating": previous["personal_score"] if previous else None,
                "status": previous["status"] if previous else "НЕ НАЧИНАЛ",
                "playtime": previous["playtime_hours"] if previous else 0.0,
                "favorite": bool(previous["favorite"]) if previous else False,
                "hidden": bool(previous["hidden"]) if previous else False,
            }
            old.update({
                "watch_count": int(previous["watch_count"] or 0) if previous else 0,
                "series_progress": f"{int(previous['season_number'] or 0)}:{int(previous['episode_number'] or 0)}" if previous else "0:0",
            })
            new = {"rating": personal_score, "status": game.status, "playtime": playtime, "favorite": bool(game.favorite), "hidden": bool(game.hidden), "watch_count": int(game.watch_count), "series_progress": f"{int(game.season_number)}:{int(game.episode_number)}"}
            now = datetime.now(timezone.utc).isoformat()
            for event_type, new_value in new.items():
                old_value = old[event_type]
                if old_value != new_value:
                    connection.execute(
                        "INSERT INTO user_activity(catalog_id,event_type,old_value,new_value,total_playtime,note,created_at) VALUES(?,?,?,?,?,?,?)",
                        (game.catalog_id, event_type, self._text(old_value), self._text(new_value), playtime, "", now),
                    )
            connection.execute("""
                INSERT INTO user_game_state(catalog_id, personal_score, status, playtime_hours, favorite, rating_criteria_json, updated_at, hidden, watch_count, season_number, episode_number)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(catalog_id) DO UPDATE SET personal_score=excluded.personal_score,
                    status=excluded.status, playtime_hours=excluded.playtime_hours,
                    favorite=excluded.favorite, rating_criteria_json=excluded.rating_criteria_json,
                    updated_at=excluded.updated_at, hidden=excluded.hidden,
                    watch_count=excluded.watch_count, season_number=excluded.season_number,
                    episode_number=excluded.episode_number
            """, (game.catalog_id, personal_score, game.status, playtime, int(game.favorite), json.dumps(game.rating_criteria, ensure_ascii=False), now, int(game.hidden), int(game.watch_count), int(game.season_number), int(game.episode_number)))
            previous_episode_states = {f"{row[0]}:{row[1]}": row[2] for row in connection.execute("SELECT season_number,episode_number,state FROM series_episode_state WHERE catalog_id=?", (game.catalog_id,))}
            if previous_episode_states != game.episode_states:
                connection.execute(
                    "INSERT INTO user_activity(catalog_id,event_type,old_value,new_value,total_playtime,note,created_at) VALUES(?,?,?,?,?,?,?)",
                    (game.catalog_id, "episode_map", self._episode_summary(previous_episode_states), self._episode_summary(game.episode_states), playtime, "", now),
                )
                connection.execute("DELETE FROM series_episode_state WHERE catalog_id=?", (game.catalog_id,))
                connection.executemany(
                    "INSERT INTO series_episode_state(catalog_id,season_number,episode_number,state,updated_at) VALUES(?,?,?,?,?)",
                    [(game.catalog_id, int(key.split(':')[0]), int(key.split(':')[1]), state, now) for key, state in game.episode_states.items()],
                )
            connection.commit()
        finally: connection.close()

    def activity_for(self, catalog_id: str) -> list[dict]:
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row
        try: rows = connection.execute("SELECT * FROM user_activity WHERE catalog_id=? ORDER BY created_at,id", (catalog_id,)).fetchall()
        finally: connection.close()
        return [dict(row) for row in rows]

    def reset_local_profile(self) -> None:
        """Delete user-owned state without touching the official catalog."""
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("DELETE FROM user_activity")
            connection.execute("DELETE FROM user_game_state")
            connection.execute("DELETE FROM series_episode_state")
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE local_profile SET display_name=?, bio='', avatar_path='', updated_at=? WHERE profile_id=1",
                ("Velora", now),
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _text(value) -> str | None:
        if value is None: return None
        if isinstance(value, bool): return "1" if value else "0"
        return str(value)

    @staticmethod
    def _format_activity(row: sqlite3.Row) -> str:
        labels = {"rating":"оценка", "status":"статус", "playtime":"время", "favorite":"избранное", "hidden":"скрытие", "watch_count":"просмотры", "series_progress":"серия", "episode_map":"эпизоды"}
        timestamp = datetime.fromisoformat(row["created_at"]).astimezone().strftime("%d.%m.%Y %H:%M")
        old_value = row["old_value"] if row["old_value"] not in (None, "") else "—"
        new_value = row["new_value"] if row["new_value"] not in (None, "") else "—"
        if row["event_type"] == "hidden":
            action = "Скрыто из каталога" if str(row["new_value"]) in ("1", "True", "true") else "Возвращено в каталог"
            return f"{timestamp} — {action}"
        suffix = f", всего {row['total_playtime']:g} ч" if row["total_playtime"] is not None and row["event_type"] in ("rating", "playtime") else ""
        return f"{timestamp} — {labels.get(row['event_type'], row['event_type'])}: {old_value} → {new_value}{suffix}"

    @staticmethod
    def _episode_summary(states: dict[str, str]) -> str:
        counts = {name: list(states.values()).count(name) for name in ("watched", "watching", "dropped")}
        return f"просмотрено {counts['watched']}, смотрю {counts['watching']}, брошено {counts['dropped']}"
