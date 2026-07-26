from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.data.user_repository import USER_DB, USER_MIGRATIONS
from app.database.migration_runner import MigrationRunner
from app.models.personal_library import ManualList, QueueEntry, ReviewDraft


class PersonalLibraryRepository:
    """Persistence for AW0.09 planning and editorial tools."""

    def __init__(self, path: Path = USER_DB) -> None:
        self.path = path
        MigrationRunner(USER_MIGRATIONS).migrate(path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def manual_lists(self) -> list[ManualList]:
        with self._connection() as connection:
            rows = connection.execute("SELECT id,name,description,cover_path,is_ranked,is_pinned FROM manual_lists WHERE deleted_at IS NULL ORDER BY is_pinned DESC,name COLLATE NOCASE").fetchall()
        return [ManualList(row[0], row[1], row[2], row[3], bool(row[4]), bool(row[5])) for row in rows]

    def save_manual_list(self, value: ManualList) -> int:
        now = self._now()
        with self._connection() as connection:
            if value.list_id is None:
                cursor = connection.execute("INSERT INTO manual_lists(name,description,cover_path,is_ranked,is_pinned,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (value.name,value.description,value.cover_path,int(value.is_ranked),int(value.is_pinned),now,now)); value.list_id=int(cursor.lastrowid)
            else:
                connection.execute("UPDATE manual_lists SET name=?,description=?,cover_path=?,is_ranked=?,is_pinned=?,updated_at=? WHERE id=? AND deleted_at IS NULL", (value.name,value.description,value.cover_path,int(value.is_ranked),int(value.is_pinned),now,value.list_id))
        return int(value.list_id)

    def list_items(self, list_id: int) -> list[dict]:
        with self._connection() as connection:
            connection.row_factory=sqlite3.Row; rows=connection.execute("SELECT * FROM manual_list_items WHERE list_id=? ORDER BY position",(list_id,)).fetchall()
        return [dict(row) for row in rows]

    def add_list_item(self, list_id: int, catalog_id: str) -> None:
        now=self._now()
        with self._connection() as connection:
            position=connection.execute("SELECT COALESCE(MAX(position),0)+1 FROM manual_list_items WHERE list_id=?",(list_id,)).fetchone()[0]
            connection.execute("INSERT OR IGNORE INTO manual_list_items(list_id,catalog_id,position,previous_position,added_at,updated_at) VALUES(?,?,?,?,?,?)",(list_id,catalog_id,position,None,now,now))

    def reorder_list(self, list_id: int, catalog_ids: list[str]) -> None:
        now=self._now()
        with self._connection() as connection:
            old={row[0]:row[1] for row in connection.execute("SELECT catalog_id,position FROM manual_list_items WHERE list_id=?",(list_id,))}
            for position,catalog_id in enumerate(catalog_ids,1):
                connection.execute("UPDATE manual_list_items SET previous_position=?,position=?,updated_at=? WHERE list_id=? AND catalog_id=?",(old.get(catalog_id),position,now,list_id,catalog_id))

    def move_list_to_trash(self, list_id: int) -> None:
        now=self._now(); expires=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat()
        with self._connection() as connection:
            row=connection.execute("SELECT name,description,cover_path,is_ranked,is_pinned FROM manual_lists WHERE id=?",(list_id,)).fetchone()
            if not row:return
            connection.execute("INSERT INTO trash_items(entity_type,entity_id,payload_json,deleted_at,expires_at) VALUES(?,?,?,?,?)",("manual_list",str(list_id),json.dumps(dict(zip(("name","description","cover_path","is_ranked","is_pinned"),row)),ensure_ascii=False),now,expires))
            connection.execute("UPDATE manual_lists SET deleted_at=? WHERE id=?",(now,list_id))

    def queue(self) -> list[QueueEntry]:
        with self._connection() as connection:
            rows=connection.execute("SELECT catalog_id,position,plan_kind,planned_date,priority,reason,goal_id FROM queue_items ORDER BY position").fetchall()
        return [QueueEntry(row[0],row[1],row[2],row[3] or "",row[4],row[5],row[6]) for row in rows]

    def save_queue_entry(self, value: QueueEntry) -> None:
        now=self._now()
        with self._connection() as connection:
            if value.position<=0:value.position=connection.execute("SELECT COALESCE(MAX(position),0)+1 FROM queue_items").fetchone()[0]
            connection.execute("INSERT INTO queue_items(catalog_id,position,plan_kind,planned_date,priority,reason,goal_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(catalog_id) DO UPDATE SET position=excluded.position,plan_kind=excluded.plan_kind,planned_date=excluded.planned_date,priority=excluded.priority,reason=excluded.reason,goal_id=excluded.goal_id,updated_at=excluded.updated_at",(value.catalog_id,value.position,value.plan_kind,value.planned_date or None,value.priority,value.reason,value.goal_id,now,now))

    def reorder_queue(self, catalog_ids: list[str]) -> None:
        now=self._now()
        with self._connection() as connection:
            for position,catalog_id in enumerate(catalog_ids,1):connection.execute("UPDATE queue_items SET position=?,updated_at=? WHERE catalog_id=?",(position,now,catalog_id))

    def remove_queue_entry(self, catalog_id: str) -> None:
        with self._connection() as connection:connection.execute("DELETE FROM queue_items WHERE catalog_id=?",(catalog_id,))
        self.reorder_queue([value.catalog_id for value in self.queue()])

    def templates(self, media_type: str = "") -> list[dict]:
        with self._connection() as connection:
            connection.row_factory=sqlite3.Row; rows=connection.execute("SELECT * FROM review_templates WHERE deleted_at IS NULL AND (?='' OR media_type=?) ORDER BY name",(media_type,media_type)).fetchall()
        return [dict(row) for row in rows]

    def save_template(self, name: str, media_type: str, body: str, template_id: int | None = None) -> int:
        now=self._now()
        with self._connection() as connection:
            if template_id is None:return int(connection.execute("INSERT INTO review_templates(name,media_type,body,created_at,updated_at) VALUES(?,?,?,?,?)",(name,media_type,body,now,now)).lastrowid)
            connection.execute("UPDATE review_templates SET name=?,media_type=?,body=?,updated_at=? WHERE id=?",(name,media_type,body,now,template_id));return template_id

    def delete_template(self, template_id: int) -> None:
        now=self._now()
        with self._connection() as connection:connection.execute("UPDATE review_templates SET deleted_at=?,updated_at=? WHERE id=?",(now,now,template_id))

    def draft(self, catalog_id: str) -> ReviewDraft | None:
        with self._connection() as connection:
            row=connection.execute("SELECT catalog_id,title,body,criteria_json,template_id,updated_at FROM review_drafts WHERE catalog_id=? AND deleted_at IS NULL",(catalog_id,)).fetchone()
        return ReviewDraft(row[0],row[1],row[2],json.loads(row[3] or "{}"),row[4],row[5]) if row else None

    def save_draft(self, value: ReviewDraft) -> None:
        now=self._now()
        with self._connection() as connection:connection.execute("INSERT INTO review_drafts(catalog_id,template_id,title,body,criteria_json,updated_at,deleted_at) VALUES(?,?,?,?,?,?,NULL) ON CONFLICT(catalog_id) DO UPDATE SET template_id=excluded.template_id,title=excluded.title,body=excluded.body,criteria_json=excluded.criteria_json,updated_at=excluded.updated_at,deleted_at=NULL",(value.catalog_id,value.template_id,value.title,value.body,json.dumps(value.criteria,ensure_ascii=False),now))

    def drafts(self) -> list[ReviewDraft]:
        with self._connection() as connection:
            rows=connection.execute("SELECT catalog_id,title,body,criteria_json,template_id,updated_at FROM review_drafts WHERE deleted_at IS NULL ORDER BY updated_at DESC").fetchall()
        return [ReviewDraft(row[0],row[1],row[2],json.loads(row[3] or "{}"),row[4],row[5]) for row in rows]

    def journal(self, catalog_id: str) -> list[dict]:
        with self._connection() as connection:
            connection.row_factory=sqlite3.Row; rows=connection.execute("SELECT * FROM journal_entries WHERE catalog_id=? AND deleted_at IS NULL ORDER BY created_at DESC",(catalog_id,)).fetchall()
        return [dict(row) for row in rows]

    def add_journal_entry(self, catalog_id: str, body: str, progress: str = "", score: float | None = None, image_path: str = "") -> None:
        now=self._now()
        with self._connection() as connection:connection.execute("INSERT INTO journal_entries(catalog_id,body,progress_value,score,image_path,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(catalog_id,body,progress,score,image_path,now,now))

    def set_archived(self, catalog_id: str, archived: bool, reason: str = "") -> None:
        with self._connection() as connection:
            if archived:connection.execute("INSERT INTO archived_items(catalog_id,reason,archived_at) VALUES(?,?,?) ON CONFLICT(catalog_id) DO UPDATE SET reason=excluded.reason,archived_at=excluded.archived_at",(catalog_id,reason,self._now()))
            else:connection.execute("DELETE FROM archived_items WHERE catalog_id=?",(catalog_id,))

    def archived_ids(self) -> set[str]:
        with self._connection() as connection:return {row[0] for row in connection.execute("SELECT catalog_id FROM archived_items")}

    def trash(self) -> list[dict]:
        with self._connection() as connection:
            connection.row_factory=sqlite3.Row; rows=connection.execute("SELECT * FROM trash_items ORDER BY deleted_at DESC").fetchall()
        return [dict(row) for row in rows]
