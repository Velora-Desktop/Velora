"""Typed repositories. They never commit and never return sqlite rows."""

from __future__ import annotations

import sqlite3

from velora_contracts.enums import (
    CatalogLifecycleState,
    LibraryMembershipState,
    MediaType,
    RatingType,
    SourceType,
)

from .models import (
    CatalogItem,
    Impression,
    JourneyEvent,
    JourneyStageFlags,
    JourneyStageMood,
    JourneyStageRating,
    JourneyStageState,
    LibraryState,
    Playthrough,
    Rating,
    SchemaMetadata,
    UserItem, Tag, UserTag,
)


class _Repository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection


class CatalogRepository(_Repository):
    def add(self, item: CatalogItem) -> None:
        self._db.execute(
            """INSERT INTO catalog_items VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.catalog_id, item.media_type.value, item.canonical_title,
                item.sort_title, item.release_year, item.short_description,
                item.description, item.lifecycle_state.value, item.revision,
                item.created_at, item.updated_at,
            ),
        )

    def get(self, catalog_id: str) -> CatalogItem | None:
        row = self._db.execute(
            "SELECT * FROM catalog_items WHERE catalog_id=?", (catalog_id,)
        ).fetchone()
        return _catalog_item(row) if row else None

    def update(self, item: CatalogItem) -> None:
        cursor = self._db.execute(
            """UPDATE catalog_items SET media_type=?,canonical_title=?,
            sort_title=?,release_year=?,short_description=?,description=?,
            lifecycle_state=?,revision=?,updated_at=? WHERE catalog_id=?""",
            (
                item.media_type.value, item.canonical_title, item.sort_title,
                item.release_year, item.short_description, item.description,
                item.lifecycle_state.value, item.revision, item.updated_at,
                item.catalog_id,
            ),
        )
        if cursor.rowcount != 1:
            raise KeyError(item.catalog_id)

    def list_all(self) -> list[CatalogItem]:
        return [_catalog_item(row) for row in self._db.execute(
            "SELECT * FROM catalog_items ORDER BY sort_title,catalog_id"
        )]

    def tags_for(self, catalog_id: str) -> list[Tag]:
        return [
            Tag(row["tag_id"], row["display_name"])
            for row in self._db.execute(
                """SELECT t.tag_id,t.display_name
                FROM catalog_tags ct JOIN tags t ON t.tag_id=ct.tag_id
                WHERE ct.catalog_id=? AND t.is_active=1
                ORDER BY ct.sort_order,t.display_name COLLATE NOCASE""",
                (catalog_id,),
            )
        ]

    def ensure_tag(self, tag: Tag) -> None:
        self._db.execute(
            """INSERT INTO tags
            (tag_id,canonical_name,display_name,is_active,revision)
            VALUES(?,?,?,1,1)
            ON CONFLICT(tag_id) DO UPDATE SET
            canonical_name=excluded.canonical_name,
            display_name=excluded.display_name,is_active=1""",
            (tag.tag_id, tag.name.casefold(), tag.name),
        )

    def assign_tag(self, catalog_id: str, tag_id: str, sort_order: int) -> None:
        self._db.execute(
            """INSERT INTO catalog_tags(catalog_id,tag_id,sort_order)
            VALUES(?,?,?)
            ON CONFLICT(catalog_id,tag_id) DO UPDATE SET
            sort_order=excluded.sort_order""",
            (catalog_id, tag_id, sort_order),
        )

    def payload(self, catalog_id: str, payload_type: str) -> tuple[int, str] | None:
        """Return an official extensible payload without leaking sqlite rows."""
        row = self._db.execute(
            """SELECT payload_version,payload_json
            FROM catalog_payloads WHERE catalog_id=? AND payload_type=?""",
            (catalog_id, payload_type),
        ).fetchone()
        return (int(row["payload_version"]), str(row["payload_json"])) if row else None

    def upsert_payload(
        self,
        catalog_id: str,
        payload_type: str,
        payload_version: int,
        payload_json: str,
        revision: int = 1,
    ) -> None:
        self._db.execute(
            """INSERT INTO catalog_payloads
            (catalog_id,payload_type,payload_version,payload_json,revision)
            VALUES(?,?,?,?,?)
            ON CONFLICT(catalog_id,payload_type) DO UPDATE SET
            payload_version=excluded.payload_version,
            payload_json=excluded.payload_json,
            revision=excluded.revision""",
            (
                catalog_id, payload_type, payload_version, payload_json,
                max(1, revision),
            ),
        )

    def delete_payload(self, catalog_id: str, payload_type: str) -> bool:
        """Delete one official extensible payload inside the caller transaction."""
        cursor = self._db.execute(
            "DELETE FROM catalog_payloads WHERE catalog_id=? AND payload_type=?",
            (catalog_id, payload_type),
        )
        return cursor.rowcount == 1


class UserItemRepository(_Repository):
    def add(self, item: UserItem) -> None:
        self._db.execute(
            "INSERT INTO user_items VALUES(?,?,?,?,?,?,?,?)",
            (item.user_item_id, item.media_type.value, item.title, item.release_year,
             item.description, item.created_at, item.updated_at, int(item.is_archived)),
        )

    def get(self, user_item_id: str) -> UserItem | None:
        row = self._db.execute(
            "SELECT * FROM user_items WHERE user_item_id=?", (user_item_id,)
        ).fetchone()
        return _user_item(row) if row else None


class UserTagRepository(_Repository):
    def list_for(self, source_type: SourceType, item_id: str) -> list[UserTag]:
        return [
            UserTag(row["node_id"], row["name"])
            for row in self._db.execute(
                """SELECT n.node_id,n.name
                FROM user_item_taxonomy it
                JOIN user_taxonomy_nodes n ON n.node_id=it.node_id
                WHERE it.source_type=? AND it.item_id=?
                  AND n.node_type='tag' AND n.is_active=1
                ORDER BY n.name COLLATE NOCASE,n.node_id""",
                (source_type.value, item_id),
            )
        ]

    def replace_for(
        self, source_type: SourceType, item_id: str, tags: list[UserTag],
    ) -> None:
        self._db.execute(
            """DELETE FROM user_item_taxonomy
            WHERE source_type=? AND item_id=? AND node_id IN
            (SELECT node_id FROM user_taxonomy_nodes WHERE node_type='tag')""",
            (source_type.value, item_id),
        )
        for tag in tags:
            existing = self._db.execute(
                """SELECT node_id FROM user_taxonomy_nodes
                WHERE parent_id IS NULL AND node_type='tag'
                  AND name=? COLLATE NOCASE""",
                (tag.name,),
            ).fetchone()
            node_id = existing["node_id"] if existing else tag.node_id
            if existing:
                self._db.execute(
                    "UPDATE user_taxonomy_nodes SET is_active=1 WHERE node_id=?",
                    (node_id,),
                )
            else:
                self._db.execute(
                    """INSERT INTO user_taxonomy_nodes
                    (node_id,parent_id,node_type,name,sort_order,is_active)
                    VALUES(?,NULL,'tag',?,0,1)""",
                    (node_id, tag.name),
                )
            self._db.execute(
                """INSERT OR IGNORE INTO user_item_taxonomy
                (source_type,item_id,node_id) VALUES(?,?,?)""",
                (source_type.value, item_id, node_id),
            )


class LibraryRepository(_Repository):
    def upsert(self, state: LibraryState) -> None:
        self._db.execute(
            """INSERT INTO user_library_state VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source_type,item_id) DO UPDATE SET
            membership_state=excluded.membership_state,favorite=excluded.favorite,
            projected_status=excluded.projected_status,
            projected_progress_value=excluded.projected_progress_value,
            projected_progress_unit=excluded.projected_progress_unit,
            projected_total_playtime_minutes=excluded.projected_total_playtime_minutes,
            started_at=excluded.started_at,completed_at=excluded.completed_at,
            archived_at=excluded.archived_at,updated_at=excluded.updated_at""",
            (
                state.source_type.value, state.item_id, state.membership_state.value,
                int(state.favorite), state.projected_status,
                state.projected_progress_value, state.projected_progress_unit,
                state.projected_total_playtime_minutes, state.started_at,
                state.completed_at, state.archived_at, state.updated_at,
            ),
        )

    def get(self, source_type: SourceType, item_id: str) -> LibraryState | None:
        row = self._db.execute(
            "SELECT * FROM user_library_state WHERE source_type=? AND item_id=?",
            (source_type.value, item_id),
        ).fetchone()
        return _library(row) if row else None

    def list_all(self) -> list[LibraryState]:
        return [_library(row) for row in self._db.execute(
            "SELECT * FROM user_library_state ORDER BY updated_at,item_id"
        )]


class PlaythroughRepository(_Repository):
    def add(self, value: Playthrough) -> None:
        self._db.execute(
            "INSERT INTO playthroughs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (value.playthrough_id, value.source_type.value, value.item_id,
             value.sequence_no, value.status, value.started_at, value.ended_at,
             value.playtime_minutes, value.progress_value, value.progress_unit,
             int(value.is_current), value.deleted_at),
        )

    def get(self, playthrough_id: str) -> Playthrough | None:
        row = self._db.execute(
            """SELECT * FROM playthroughs
            WHERE playthrough_id=? AND deleted_at IS NULL""", (playthrough_id,)
        ).fetchone()
        return _playthrough(row) if row else None

    def get_including_deleted(self, playthrough_id: str) -> Playthrough | None:
        row = self._db.execute(
            "SELECT * FROM playthroughs WHERE playthrough_id=?", (playthrough_id,)
        ).fetchone()
        return _playthrough(row) if row else None

    def update_state(
        self, playthrough_id: str, *, status: str, playtime_minutes: int,
        progress_value: float | None = None, progress_unit: str | None = None,
        started_at: str | None = None, ended_at: str | None = None,
    ) -> None:
        self._db.execute(
            """UPDATE playthroughs SET status=?,playtime_minutes=?,
            progress_value=?,progress_unit=?,started_at=?,ended_at=?
            WHERE playthrough_id=?""",
            (status, playtime_minutes, progress_value, progress_unit, started_at,
             ended_at, playthrough_id),
        )

    def get_current(self, source_type: SourceType, item_id: str) -> Playthrough | None:
        row = self._db.execute(
            """SELECT * FROM playthroughs WHERE source_type=? AND item_id=?
            AND is_current=1 AND deleted_at IS NULL""", (source_type.value, item_id)
        ).fetchone()
        return _playthrough(row) if row else None

    def retire_current(self, source_type: SourceType, item_id: str) -> None:
        self._db.execute(
            """UPDATE playthroughs SET is_current=0
            WHERE source_type=? AND item_id=? AND is_current=1""",
            (source_type.value, item_id),
        )

    def list_for_item(self, source_type: SourceType, item_id: str) -> list[Playthrough]:
        return [_playthrough(row) for row in self._db.execute(
            """SELECT * FROM playthroughs WHERE source_type=? AND item_id=?
            AND deleted_at IS NULL ORDER BY sequence_no""",
            (source_type.value, item_id)
        )]

    def set_current(self, playthrough_id: str) -> None:
        self._db.execute(
            "UPDATE playthroughs SET is_current=1 WHERE playthrough_id=?",
            (playthrough_id,),
        )

    def soft_delete(self, playthrough_id: str, deleted_at: str) -> None:
        self._db.execute(
            """UPDATE playthroughs SET is_current=0,deleted_at=?
            WHERE playthrough_id=? AND deleted_at IS NULL""",
            (deleted_at, playthrough_id),
        )

    def delete_personal_data(self, playthrough_id: str) -> None:
        # Schema 1 uses SET NULL for ratings/events, so these records must be
        # removed explicitly rather than detached from their deleted run.
        self._db.execute(
            "DELETE FROM user_ratings WHERE playthrough_id=?", (playthrough_id,)
        )
        self._db.execute(
            "DELETE FROM journey_events WHERE playthrough_id=?", (playthrough_id,)
        )
        # The remaining playthrough-owned tables use ON DELETE CASCADE, but a
        # tombstone is retained to preserve sequence history. Clear them here.
        self._db.execute(
            "DELETE FROM impressions WHERE playthrough_id=?", (playthrough_id,)
        )
        self._db.execute(
            "DELETE FROM journey_stage_moods WHERE playthrough_id=?",
            (playthrough_id,),
        )
        self._db.execute(
            "DELETE FROM journey_stage_states WHERE playthrough_id=?",
            (playthrough_id,),
        )
        self._db.execute(
            "DELETE FROM journey_stage_ratings WHERE playthrough_id=?",
            (playthrough_id,),
        )
        self._db.execute(
            "DELETE FROM journey_stage_flags WHERE playthrough_id=?",
            (playthrough_id,),
        )

    def next_sequence(self, source_type: SourceType, item_id: str) -> int:
        return int(self._db.execute(
            """SELECT COALESCE(MAX(sequence_no),0)+1 FROM playthroughs
            WHERE source_type=? AND item_id=?""", (source_type.value, item_id)
        ).fetchone()[0])


class JourneyRepository(_Repository):
    def append(self, value: JourneyEvent) -> None:
        self._db.execute(
            "INSERT INTO journey_events VALUES(?,?,?,?,?,?,?,?,?)",
            (value.event_id, value.operation_id, value.source_type.value,
             value.item_id, value.playthrough_id, value.event_type,
             value.payload_version, value.payload_json, value.occurred_at),
        )

    def get_by_operation(self, operation_id: str) -> JourneyEvent | None:
        row = self._db.execute(
            "SELECT * FROM journey_events WHERE operation_id=?", (operation_id,)
        ).fetchone()
        return _journey(row) if row else None

    def list_for_item(self, source_type: SourceType, item_id: str) -> list[JourneyEvent]:
        return [_journey(row) for row in self._db.execute(
            """SELECT * FROM journey_events WHERE source_type=? AND item_id=?
            ORDER BY occurred_at,event_id""", (source_type.value, item_id)
        )]

    def latest_of_type(
        self, source_type: SourceType, item_id: str, event_type: str
    ) -> JourneyEvent | None:
        row = self._db.execute(
            """SELECT * FROM journey_events WHERE source_type=? AND item_id=?
            AND event_type=? ORDER BY occurred_at DESC,event_id DESC LIMIT 1""",
            (source_type.value, item_id, event_type),
        ).fetchone()
        return _journey(row) if row else None


class RatingRepository(_Repository):
    def add(self, value: Rating) -> None:
        self._db.execute(
            "INSERT INTO user_ratings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (value.rating_id, value.source_type.value, value.item_id,
             value.playthrough_id, value.rating_type.value, value.checkpoint_type,
             value.value_tenths, value.review_text, int(value.is_current),
             value.superseded_at, value.created_at, value.updated_at),
        )

    def get_current_final(self, source_type: SourceType, item_id: str) -> Rating | None:
        row = self._db.execute(
            """SELECT * FROM user_ratings WHERE source_type=? AND item_id=?
            AND rating_type='final' AND is_current=1""",
            (source_type.value, item_id),
        ).fetchone()
        return _rating(row) if row else None

    def get(self, rating_id: str) -> Rating | None:
        row = self._db.execute(
            "SELECT * FROM user_ratings WHERE rating_id=?", (rating_id,)
        ).fetchone()
        return _rating(row) if row else None

    def get_current_checkpoint(
        self, playthrough_id: str, checkpoint_type: str
    ) -> Rating | None:
        row = self._db.execute(
            """SELECT * FROM user_ratings WHERE playthrough_id=? AND checkpoint_type=?
            AND rating_type='checkpoint' AND is_current=1""",
            (playthrough_id, checkpoint_type),
        ).fetchone()
        return _rating(row) if row else None

    def supersede_current_final(
        self, source_type: SourceType, item_id: str, occurred_at: str
    ) -> None:
        self._db.execute(
            """UPDATE user_ratings SET is_current=0,superseded_at=?,updated_at=?
            WHERE source_type=? AND item_id=? AND rating_type='final' AND is_current=1""",
            (occurred_at, occurred_at, source_type.value, item_id),
        )

    def supersede_current_checkpoint(
        self, playthrough_id: str, checkpoint_type: str, occurred_at: str
    ) -> None:
        self._db.execute(
            """UPDATE user_ratings SET is_current=0,superseded_at=?,updated_at=?
            WHERE playthrough_id=? AND checkpoint_type=? AND rating_type='checkpoint'
            AND is_current=1""",
            (occurred_at, occurred_at, playthrough_id, checkpoint_type),
        )

    def add_criterion(
        self, criterion_rating_id: str, rating_id: str,
        criterion_code: str, value_tenths: int,
    ) -> None:
        self._db.execute(
            "INSERT INTO rating_criteria VALUES(?,?,?,?)",
            (criterion_rating_id, rating_id, criterion_code, value_tenths),
        )

    def history(self, source_type: SourceType, item_id: str) -> list[Rating]:
        return [_rating(row) for row in self._db.execute(
            """SELECT * FROM user_ratings WHERE source_type=? AND item_id=?
            ORDER BY created_at,rating_id""", (source_type.value, item_id)
        )]

    def restore_latest_final(
        self, source_type: SourceType, item_id: str, updated_at: str,
    ) -> None:
        row = self._db.execute(
            """SELECT rating_id FROM user_ratings
            WHERE source_type=? AND item_id=? AND rating_type='final'
            ORDER BY created_at DESC,rating_id DESC LIMIT 1""",
            (source_type.value, item_id),
        ).fetchone()
        if row is not None:
            self._db.execute(
                """UPDATE user_ratings SET is_current=1,superseded_at=NULL,
                updated_at=? WHERE rating_id=?""",
                (updated_at, row["rating_id"]),
            )


class JourneyStageMoodRepository(_Repository):
    def set(self, playthrough_id: str, stage_id: str, mood_id: str, updated_at: str) -> None:
        self._db.execute(
            """INSERT INTO journey_stage_moods(playthrough_id,stage_id,mood_id,updated_at)
            VALUES(?,?,?,?) ON CONFLICT(playthrough_id,stage_id) DO UPDATE SET
            mood_id=excluded.mood_id,updated_at=excluded.updated_at""",
            (playthrough_id, stage_id, mood_id, updated_at),
        )

    def clear(self, playthrough_id: str, stage_id: str) -> None:
        self._db.execute(
            "DELETE FROM journey_stage_moods WHERE playthrough_id=? AND stage_id=?",
            (playthrough_id, stage_id),
        )

    def list_for_playthrough(self, playthrough_id: str) -> dict[str, str]:
        return {
            row["stage_id"]: row["mood_id"]
            for row in self._db.execute(
                """SELECT stage_id,mood_id FROM journey_stage_moods
                WHERE playthrough_id=? ORDER BY stage_id""", (playthrough_id,)
            )
        }

    def list_records_for_playthrough(
        self, playthrough_id: str,
    ) -> list[JourneyStageMood]:
        return [
            JourneyStageMood(
                row["playthrough_id"], row["stage_id"], row["mood_id"],
                row["updated_at"],
            )
            for row in self._db.execute(
                """SELECT playthrough_id,stage_id,mood_id,updated_at
                FROM journey_stage_moods WHERE playthrough_id=?
                ORDER BY stage_id""",
                (playthrough_id,),
            )
        ]


class JourneyStageStateRepository(_Repository):
    ALLOWED = frozenset((
        "not_started", "current", "in_progress", "completed", "skipped",
    ))

    def set(
        self, playthrough_id: str, stage_id: str, state: str, updated_at: str,
    ) -> None:
        if state not in self.ALLOWED:
            raise ValueError(f"Unknown Journey stage state: {state}")
        self._db.execute(
            """INSERT INTO journey_stage_states(
            playthrough_id,stage_id,state,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(playthrough_id,stage_id) DO UPDATE SET
            state=excluded.state,updated_at=excluded.updated_at""",
            (playthrough_id, stage_id, state, updated_at),
        )

    def list_for_playthrough(self, playthrough_id: str) -> dict[str, str]:
        return {
            row["stage_id"]: row["state"]
            for row in self._db.execute(
                """SELECT stage_id,state FROM journey_stage_states
                WHERE playthrough_id=? ORDER BY stage_id""", (playthrough_id,)
            )
        }

    def list_records_for_playthrough(
        self, playthrough_id: str,
    ) -> list[JourneyStageState]:
        return [
            JourneyStageState(
                row["playthrough_id"], row["stage_id"], row["state"],
                row["updated_at"],
            )
            for row in self._db.execute(
                """SELECT playthrough_id,stage_id,state,updated_at
                FROM journey_stage_states WHERE playthrough_id=?
                ORDER BY stage_id""",
                (playthrough_id,),
            )
        ]


class JourneyStageRatingRepository(_Repository):
    def set(self, playthrough_id: str, stage_id: str, value_tenths: int, updated_at: str) -> None:
        if not 10 <= value_tenths <= 100:
            raise ValueError("Journey stage rating must be between 10 and 100")
        self._db.execute(
            """INSERT INTO journey_stage_ratings(playthrough_id,stage_id,value_tenths,updated_at)
            VALUES(?,?,?,?) ON CONFLICT(playthrough_id,stage_id) DO UPDATE SET
            value_tenths=excluded.value_tenths,updated_at=excluded.updated_at""",
            (playthrough_id, stage_id, value_tenths, updated_at),
        )

    def get(self, playthrough_id: str, stage_id: str) -> int | None:
        row = self._db.execute(
            "SELECT value_tenths FROM journey_stage_ratings WHERE playthrough_id=? AND stage_id=?",
            (playthrough_id, stage_id),
        ).fetchone()
        return int(row["value_tenths"]) if row else None

    def list_for_playthrough(self, playthrough_id: str) -> dict[str, int]:
        return {row["stage_id"]: int(row["value_tenths"]) for row in self._db.execute(
            """SELECT stage_id,value_tenths FROM journey_stage_ratings
            WHERE playthrough_id=? ORDER BY stage_id""", (playthrough_id,)
        )}

    def list_records_for_playthrough(self, playthrough_id: str) -> list[JourneyStageRating]:
        return [JourneyStageRating(
            row["playthrough_id"], row["stage_id"], int(row["value_tenths"]),
            row["updated_at"],
        ) for row in self._db.execute(
            """SELECT playthrough_id,stage_id,value_tenths,updated_at
            FROM journey_stage_ratings WHERE playthrough_id=? ORDER BY stage_id""",
            (playthrough_id,),
        )]


class JourneyStageFlagsRepository(_Repository):
    def set(self, playthrough_id: str, stage_id: str, *, favorite: bool,
            difficult: bool, updated_at: str) -> None:
        self._db.execute(
            """INSERT INTO journey_stage_flags(
            playthrough_id,stage_id,favorite,difficult,updated_at) VALUES(?,?,?,?,?)
            ON CONFLICT(playthrough_id,stage_id) DO UPDATE SET
            favorite=excluded.favorite,difficult=excluded.difficult,
            updated_at=excluded.updated_at""",
            (playthrough_id, stage_id, int(favorite), int(difficult), updated_at),
        )

    def get(self, playthrough_id: str, stage_id: str) -> tuple[bool, bool]:
        row = self._db.execute(
            """SELECT favorite,difficult FROM journey_stage_flags
            WHERE playthrough_id=? AND stage_id=?""", (playthrough_id, stage_id)
        ).fetchone()
        return (bool(row["favorite"]), bool(row["difficult"])) if row else (False, False)

    def list_for_playthrough(self, playthrough_id: str) -> dict[str, tuple[bool, bool]]:
        return {row["stage_id"]: (bool(row["favorite"]), bool(row["difficult"]))
                for row in self._db.execute(
                    """SELECT stage_id,favorite,difficult FROM journey_stage_flags
                    WHERE playthrough_id=? ORDER BY stage_id""", (playthrough_id,))}

    def list_records_for_playthrough(self, playthrough_id: str) -> list[JourneyStageFlags]:
        return [JourneyStageFlags(
            row["playthrough_id"], row["stage_id"], bool(row["favorite"]),
            bool(row["difficult"]), row["updated_at"],
        ) for row in self._db.execute(
            """SELECT playthrough_id,stage_id,favorite,difficult,updated_at
            FROM journey_stage_flags WHERE playthrough_id=? ORDER BY stage_id""",
            (playthrough_id,),
        )]


class ImpressionRepository(_Repository):
    def add(self, value: Impression) -> None:
        self._db.execute(
            "INSERT INTO impressions VALUES(?,?,?,?,?,?,?,?)",
            (value.impression_id, value.playthrough_id, value.checkpoint_type,
             value.text, value.progress_value, value.progress_unit,
             value.playtime_minutes_at_entry, value.created_at),
        )

    def get(self, impression_id: str) -> Impression | None:
        row = self._db.execute(
            "SELECT * FROM impressions WHERE impression_id=?", (impression_id,)
        ).fetchone()
        return _impression(row) if row else None

    def latest_for_playthrough(self, playthrough_id: str) -> Impression | None:
        row = self._db.execute(
            """SELECT * FROM impressions WHERE playthrough_id=?
            ORDER BY created_at DESC,impression_id DESC LIMIT 1""",
            (playthrough_id,),
        ).fetchone()
        return _impression(row) if row else None

    def list_for_playthrough(self, playthrough_id: str) -> list[Impression]:
        return [_impression(row) for row in self._db.execute(
            """SELECT * FROM impressions WHERE playthrough_id=?
            ORDER BY created_at,impression_id""",
            (playthrough_id,),
        )]


class SystemStateRepository(_Repository):
    def schema_metadata(self) -> SchemaMetadata:
        row = self._db.execute("SELECT * FROM schema_meta WHERE singleton_id=1").fetchone()
        if row is None:
            raise LookupError("schema_meta row is missing")
        names = set(row.keys())
        return SchemaMetadata(
            schema_version=row["schema_version"],
            contract_version=row["contract_version"],
            core_generation=row["core_generation"],
            reset_boundary=row["reset_boundary"] if "reset_boundary" in names else None,
            reset_operation_id=row["reset_operation_id"] if "reset_operation_id" in names else None,
            reset_state=row["reset_state"] if "reset_state" in names else None,
            updated_at=row["updated_at"],
        )


def _catalog_item(r: sqlite3.Row) -> CatalogItem:
    return CatalogItem(r["catalog_id"], MediaType(r["media_type"]), r["canonical_title"],
        r["sort_title"], r["release_year"], r["short_description"], r["description"],
        CatalogLifecycleState(r["lifecycle_state"]), r["revision"], r["created_at"], r["updated_at"])

def _user_item(r: sqlite3.Row) -> UserItem:
    return UserItem(r["user_item_id"], MediaType(r["media_type"]), r["title"],
        r["release_year"], r["description"], r["created_at"], r["updated_at"], bool(r["is_archived"]))

def _library(r: sqlite3.Row) -> LibraryState:
    return LibraryState(SourceType(r["source_type"]), r["item_id"],
        LibraryMembershipState(r["membership_state"]), bool(r["favorite"]),
        r["projected_status"], r["projected_progress_value"], r["projected_progress_unit"],
        r["projected_total_playtime_minutes"], r["started_at"], r["completed_at"],
        r["archived_at"], r["updated_at"])

def _playthrough(r: sqlite3.Row) -> Playthrough:
    return Playthrough(r["playthrough_id"], SourceType(r["source_type"]), r["item_id"],
        r["sequence_no"], r["status"], r["started_at"], r["ended_at"],
        r["playtime_minutes"], r["progress_value"], r["progress_unit"],
        bool(r["is_current"]), r["deleted_at"])

def _journey(r: sqlite3.Row) -> JourneyEvent:
    return JourneyEvent(r["event_id"], r["operation_id"], SourceType(r["source_type"]),
        r["item_id"], r["playthrough_id"], r["event_type"], r["payload_version"],
        r["payload_json"], r["occurred_at"])

def _rating(r: sqlite3.Row) -> Rating:
    return Rating(r["rating_id"], SourceType(r["source_type"]), r["item_id"],
        r["playthrough_id"], RatingType(r["rating_type"]), r["checkpoint_type"],
        r["value_tenths"], r["review_text"], bool(r["is_current"]),
        r["superseded_at"], r["created_at"], r["updated_at"])

def _impression(r: sqlite3.Row) -> Impression:
    return Impression(r["impression_id"], r["playthrough_id"], r["checkpoint_type"],
        r["text"], r["progress_value"], r["progress_unit"],
        r["playtime_minutes_at_entry"], r["created_at"])
