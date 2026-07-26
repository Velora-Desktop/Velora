from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.database.migration_runner import MigrationRunner
from app.models.personal_library import ActivityEntry, SmartListDefinition, UserGoal


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
            notes = {row["catalog_id"]: row["note"] for row in connection.execute("SELECT catalog_id,note FROM user_notes")}
            tags: dict[str, list[str]] = {}
            for row in connection.execute("SELECT uit.catalog_id,ut.name FROM user_item_tags uit JOIN user_tags ut ON ut.id=uit.tag_id ORDER BY ut.name"):
                tags.setdefault(row["catalog_id"], []).append(row["name"])
            archived = {row["catalog_id"] for row in connection.execute("SELECT catalog_id FROM archived_items")}
        finally: connection.close()
        for game in games:
            state = states.get(game.catalog_id)
            game.note = notes.get(game.catalog_id, "")
            game.tags = tags.get(game.catalog_id, [])
            game.archived = game.catalog_id in archived
            if state is None: continue
            game.personal_score = "—" if state["personal_score"] is None else f'{state["personal_score"]:.1f}'
            game.status = state["status"] or game.status
            game.playtime_hours = float(state["playtime_hours"] or 0.0) if game.media_type == "Игры" else 0.0
            game.favorite = bool(state["favorite"])
            game.rating_criteria = json.loads(state["rating_criteria_json"] or "{}")
            game.hidden = bool(state["hidden"])
            game.watch_count = int(state["watch_count"] or 0)
            game.season_number = int(state["season_number"] or 0)
            game.episode_number = int(state["episode_number"] or 0)
            game.episode_states = episode_states.get(game.catalog_id, {})
            game.user_interacted = True
            game.interaction_started_at = state["interaction_started_at"] or ""
            game.interaction_completed_at = state["interaction_completed_at"] or ""
            game.history = [self._format_activity(row) for row in activities.get(game.catalog_id, [])]

    def save_game_state(self, game) -> None:
        try: personal_score = float(game.personal_score)
        except ValueError: personal_score = None
        playtime = float(game.playtime_hours) if game.media_type == "Игры" else 0.0
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
            started_at = (previous["interaction_started_at"] if previous else None) or game.interaction_started_at or now
            completed_statuses = {"ПРОШЁЛ", "ПОСМОТРЕЛ", "ИСПОЛЬЗОВАЛ"}
            completed_at = (previous["interaction_completed_at"] if previous else None) or game.interaction_completed_at or None
            if game.status in completed_statuses and not completed_at:
                completed_at = now
            game.interaction_started_at = started_at
            game.interaction_completed_at = completed_at or ""
            for event_type, new_value in new.items():
                old_value = old[event_type]
                if old_value != new_value:
                    connection.execute(
                        "INSERT INTO user_activity(catalog_id,event_type,old_value,new_value,total_playtime,note,created_at) VALUES(?,?,?,?,?,?,?)",
                        (game.catalog_id, event_type, self._text(old_value), self._text(new_value), playtime, "", now),
                    )
            connection.execute("""
                INSERT INTO user_game_state(catalog_id, personal_score, status, playtime_hours, favorite, rating_criteria_json, updated_at, hidden, watch_count, season_number, episode_number, interaction_started_at, interaction_completed_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(catalog_id) DO UPDATE SET personal_score=excluded.personal_score,
                    status=excluded.status, playtime_hours=excluded.playtime_hours,
                    favorite=excluded.favorite, rating_criteria_json=excluded.rating_criteria_json,
                    updated_at=excluded.updated_at, hidden=excluded.hidden,
                    watch_count=excluded.watch_count, season_number=excluded.season_number,
                    episode_number=excluded.episode_number,
                    interaction_started_at=excluded.interaction_started_at,
                    interaction_completed_at=excluded.interaction_completed_at
            """, (game.catalog_id, personal_score, game.status, playtime, int(game.favorite), json.dumps(game.rating_criteria, ensure_ascii=False), now, int(game.hidden), int(game.watch_count), int(game.season_number), int(game.episode_number), started_at, completed_at))
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

    def all_activity(self, limit: int = 500) -> list[dict]:
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute("SELECT * FROM user_activity ORDER BY created_at DESC,id DESC LIMIT ?", (limit,)).fetchall()
        finally: connection.close()
        return [dict(row) for row in rows]

    def save_note(self, catalog_id: str, note: str) -> None:
        now = datetime.now(timezone.utc).isoformat(); connection = sqlite3.connect(self.path)
        try:
            previous = connection.execute("SELECT note FROM user_notes WHERE catalog_id=?", (catalog_id,)).fetchone()
            old = previous[0] if previous else ""
            connection.execute("INSERT INTO user_notes(catalog_id,note,updated_at) VALUES(?,?,?) ON CONFLICT(catalog_id) DO UPDATE SET note=excluded.note,updated_at=excluded.updated_at", (catalog_id, note, now))
            if old != note:
                connection.execute("INSERT INTO user_activity(catalog_id,event_type,old_value,new_value,total_playtime,note,created_at) VALUES(?,?,?,?,?,?,?)", (catalog_id, "note", old, note, None, "", now))
            connection.commit()
        finally: connection.close()

    def smart_lists(self) -> list[SmartListDefinition]:
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row
        try: rows = connection.execute("SELECT * FROM smart_lists ORDER BY name COLLATE NOCASE").fetchall()
        finally: connection.close()
        return [SmartListDefinition(row["id"], row["name"], row["media_type"], json.loads(row["rules_json"] or "{}"), bool(row["is_system"])) for row in rows]

    def save_smart_list(self, definition: SmartListDefinition) -> int:
        now = datetime.now(timezone.utc).isoformat(); connection = sqlite3.connect(self.path)
        try:
            if definition.list_id is None:
                cursor = connection.execute("INSERT INTO smart_lists(name,media_type,rules_json,is_system,created_at,updated_at) VALUES(?,?,?,?,?,?)", (definition.name, definition.media_type, json.dumps(definition.rules, ensure_ascii=False), int(definition.is_system), now, now))
                definition.list_id = int(cursor.lastrowid)
            else:
                connection.execute("UPDATE smart_lists SET name=?,media_type=?,rules_json=?,updated_at=? WHERE id=? AND is_system=0", (definition.name, definition.media_type, json.dumps(definition.rules, ensure_ascii=False), now, definition.list_id))
            connection.commit(); return int(definition.list_id)
        finally: connection.close()

    def delete_smart_list(self, list_id: int) -> None:
        connection = sqlite3.connect(self.path)
        try: connection.execute("DELETE FROM smart_lists WHERE id=? AND is_system=0", (list_id,)); connection.commit()
        finally: connection.close()

    def tags(self) -> list[tuple[int, str, str, int]]:
        connection = sqlite3.connect(self.path)
        try: return connection.execute("SELECT t.id,t.name,t.color,COUNT(it.catalog_id) FROM user_tags t LEFT JOIN user_item_tags it ON it.tag_id=t.id GROUP BY t.id ORDER BY t.name COLLATE NOCASE").fetchall()
        finally: connection.close()

    def tag_ids_for(self, catalog_id: str) -> list[int]:
        connection=sqlite3.connect(self.path)
        try:return [int(row[0]) for row in connection.execute("SELECT tag_id FROM user_item_tags WHERE catalog_id=?",(catalog_id,)).fetchall()]
        finally:connection.close()

    def add_tag(self, name: str, color: str = "#8B2CF5") -> int:
        connection = sqlite3.connect(self.path); now = datetime.now(timezone.utc).isoformat()
        try:
            connection.execute("INSERT OR IGNORE INTO user_tags(name,color,created_at) VALUES(?,?,?)", (name.strip(), color, now))
            row = connection.execute("SELECT id FROM user_tags WHERE name=? COLLATE NOCASE", (name.strip(),)).fetchone(); connection.commit(); return int(row[0])
        finally: connection.close()

    def assign_tag(self, catalog_id: str, tag_id: int, assigned: bool = True) -> None:
        connection = sqlite3.connect(self.path); now = datetime.now(timezone.utc).isoformat()
        try:
            if assigned: connection.execute("INSERT OR IGNORE INTO user_item_tags(catalog_id,tag_id,created_at) VALUES(?,?,?)", (catalog_id, tag_id, now))
            else: connection.execute("DELETE FROM user_item_tags WHERE catalog_id=? AND tag_id=?", (catalog_id, tag_id))
            connection.execute("INSERT INTO user_activity(catalog_id,event_type,old_value,new_value,total_playtime,note,created_at) VALUES(?,?,?,?,?,?,?)", (catalog_id, "tag", "", str(tag_id) if assigned else "", None, "added" if assigned else "removed", now))
            connection.commit()
        finally: connection.close()

    def goals(self) -> list[UserGoal]:
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row
        try: rows = connection.execute("SELECT * FROM user_goals ORDER BY completed_at IS NOT NULL,deadline IS NULL,deadline,created_at DESC").fetchall()
        finally: connection.close()
        return [UserGoal(row["id"], row["title"], row["metric"], row["target_value"], row["current_value"], row["media_type"], row["deadline"] or "", row["completed_at"] or "") for row in rows]

    def save_goal(self, goal: UserGoal) -> int:
        now = datetime.now(timezone.utc).isoformat(); completed = goal.completed_at or (now if goal.current_value >= goal.target_value else None); connection = sqlite3.connect(self.path)
        try:
            if goal.goal_id is None:
                cursor = connection.execute("INSERT INTO user_goals(title,media_type,metric,target_value,current_value,deadline,completed_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (goal.title,goal.media_type,goal.metric,goal.target_value,goal.current_value,goal.deadline or None,completed,now,now)); goal.goal_id=int(cursor.lastrowid)
            else:
                connection.execute("UPDATE user_goals SET title=?,media_type=?,metric=?,target_value=?,current_value=?,deadline=?,completed_at=?,updated_at=? WHERE id=?", (goal.title,goal.media_type,goal.metric,goal.target_value,goal.current_value,goal.deadline or None,completed,now,goal.goal_id))
            connection.commit(); return int(goal.goal_id)
        finally: connection.close()

    def add_interaction_session(self, catalog_id: str, session_type: str, value: float = 0, note: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat(); connection = sqlite3.connect(self.path)
        try:
            number = connection.execute("SELECT COUNT(*)+1 FROM interaction_sessions WHERE catalog_id=? AND session_type=?", (catalog_id,session_type)).fetchone()[0]
            connection.execute("INSERT INTO interaction_sessions(catalog_id,session_type,sequence_number,value,note,occurred_at) VALUES(?,?,?,?,?,?)", (catalog_id,session_type,number,value,note,now))
            connection.execute("INSERT INTO user_activity(catalog_id,event_type,old_value,new_value,total_playtime,note,created_at) VALUES(?,?,?,?,?,?,?)", (catalog_id,"repeat","",str(number),value,note,now)); connection.commit()
        finally: connection.close()

    def reset_local_profile(self) -> None:
        """Delete user-owned state without touching the official catalog."""
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("DELETE FROM user_activity")
            connection.execute("DELETE FROM user_game_state")
            connection.execute("DELETE FROM series_episode_state")
            connection.execute("DELETE FROM smart_lists")
            connection.execute("DELETE FROM user_notes")
            connection.execute("DELETE FROM user_item_tags")
            connection.execute("DELETE FROM user_tags")
            connection.execute("DELETE FROM user_goals")
            connection.execute("DELETE FROM interaction_sessions")
            connection.execute("DELETE FROM manual_list_items")
            connection.execute("DELETE FROM manual_lists")
            connection.execute("DELETE FROM queue_items")
            connection.execute("DELETE FROM review_drafts")
            connection.execute("DELETE FROM review_templates")
            connection.execute("DELETE FROM journal_entries")
            connection.execute("DELETE FROM saved_filters")
            connection.execute("DELETE FROM archived_items")
            connection.execute("DELETE FROM trash_items")
            connection.execute("DELETE FROM custom_catalog_items")
            connection.execute("DELETE FROM custom_catalog_branches")
            connection.execute("DELETE FROM custom_sections")
            connection.execute("DELETE FROM pinned_items")
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
        labels = {"rating":"оценка", "status":"статус", "playtime":"время", "favorite":"избранное", "hidden":"скрытие", "watch_count":"просмотры", "series_progress":"серия", "episode_map":"эпизоды", "note":"заметка", "tag":"тег", "repeat":"повтор"}
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
