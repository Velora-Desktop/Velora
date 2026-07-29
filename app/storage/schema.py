"""Frozen AW0.2 Schema 1 creators and validation."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from velora_contracts.errors import IntegrityError, ValidationError

from .sqlite_policy import SQLitePolicy

SCHEMA_VERSION = 1
CONTRACT_VERSION = 1
CORE_GENERATION = 1
CATALOG_VERSION = "0.21"
RESET_BOUNDARY = "aw0.2_core_boundary"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


CATALOG_SCHEMA = """
CREATE TABLE schema_meta(singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),schema_version INTEGER NOT NULL,contract_version INTEGER NOT NULL,core_generation INTEGER NOT NULL,reset_boundary TEXT NULL,reset_operation_id TEXT NULL,reset_state TEXT NULL CHECK(reset_state IN ('completed')),updated_at TEXT NOT NULL);
CREATE TABLE catalog_items(catalog_id TEXT PRIMARY KEY,media_type TEXT NOT NULL CHECK(media_type IN ('game','film','series','program')),canonical_title TEXT NOT NULL,sort_title TEXT NOT NULL,release_year INTEGER NULL,short_description TEXT NULL,description TEXT NULL,lifecycle_state TEXT NOT NULL DEFAULT 'active' CHECK(lifecycle_state IN ('active','retired','withdrawn')),revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1),created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX ix_catalog_media_sort ON catalog_items(media_type,sort_title); CREATE INDEX ix_catalog_year ON catalog_items(release_year); CREATE INDEX ix_catalog_lifecycle ON catalog_items(lifecycle_state);
CREATE TABLE catalog_external_ids(catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,provider TEXT NOT NULL,external_id TEXT NOT NULL,url TEXT NULL,PRIMARY KEY(provider,external_id),UNIQUE(catalog_id,provider,external_id));
CREATE TABLE catalog_titles(title_id TEXT PRIMARY KEY,catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,title TEXT NOT NULL,language_code TEXT NULL,region_code TEXT NULL,title_type TEXT NOT NULL CHECK(title_type IN ('alternate','localized','original','working')),is_searchable INTEGER NOT NULL DEFAULT 1 CHECK(is_searchable IN (0,1)),revision INTEGER NOT NULL DEFAULT 1,UNIQUE(catalog_id,title,language_code,region_code,title_type));
CREATE INDEX ix_catalog_titles_item ON catalog_titles(catalog_id);
CREATE TABLE companies(company_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL COLLATE NOCASE UNIQUE,display_name TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE company_roles(role_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE platforms(platform_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE releases(release_id TEXT PRIMARY KEY,catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,platform_id TEXT NULL REFERENCES platforms,region_code TEXT NULL,release_date TEXT NULL,release_precision TEXT NOT NULL DEFAULT 'day' CHECK(release_precision IN ('day','month','year','unknown')),edition_name TEXT NULL,is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE INDEX ix_releases_item_date ON releases(catalog_id,release_date);
CREATE TABLE catalog_companies(catalog_company_id TEXT PRIMARY KEY,catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,company_id TEXT NOT NULL REFERENCES companies,role_id TEXT NOT NULL REFERENCES company_roles,release_id TEXT NULL REFERENCES releases ON DELETE CASCADE,revision INTEGER NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX uq_catalog_company_item ON catalog_companies(catalog_id,company_id,role_id) WHERE release_id IS NULL;
CREATE UNIQUE INDEX uq_catalog_company_release ON catalog_companies(catalog_id,company_id,role_id,release_id) WHERE release_id IS NOT NULL;
CREATE TABLE genres(genre_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE tags(tag_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE catalog_genres(catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,genre_id TEXT NOT NULL REFERENCES genres,sort_order INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(catalog_id,genre_id));
CREATE TABLE catalog_tags(catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,tag_id TEXT NOT NULL REFERENCES tags,sort_order INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(catalog_id,tag_id));
CREATE TABLE relations(relation_id TEXT PRIMARY KEY,source_catalog_id TEXT NOT NULL REFERENCES catalog_items,target_catalog_id TEXT NOT NULL REFERENCES catalog_items,relation_type TEXT NOT NULL CHECK(relation_type IN ('sequel','prequel','spin_off','remake','remaster','expansion','same_series','alternate_version','spiritual_successor')),series_order REAL NULL,story_order REAL NULL,note TEXT NULL,revision INTEGER NOT NULL DEFAULT 1,CHECK(source_catalog_id<>target_catalog_id),UNIQUE(source_catalog_id,target_catalog_id,relation_type));
CREATE TABLE catalog_redirects(old_catalog_id TEXT PRIMARY KEY,target_catalog_id TEXT NOT NULL REFERENCES catalog_items,reason TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE catalog_ratings(rating_id TEXT PRIMARY KEY,catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,rating_kind TEXT NOT NULL CHECK(rating_kind IN ('critic','audience')),source_name TEXT NOT NULL,raw_value REAL NOT NULL,raw_scale_max REAL NOT NULL CHECK(raw_scale_max>0),normalized_value_tenths INTEGER NOT NULL CHECK(normalized_value_tenths BETWEEN 0 AND 100),vote_count INTEGER NULL CHECK(vote_count IS NULL OR vote_count>=0),observed_at TEXT NOT NULL,source_url TEXT NULL,is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN(0,1)),revision INTEGER NOT NULL DEFAULT 1,UNIQUE(catalog_id,rating_kind,source_name,observed_at));
CREATE UNIQUE INDEX uq_catalog_rating_current ON catalog_ratings(catalog_id,rating_kind,source_name) WHERE is_current=1;
CREATE TABLE game_duration(catalog_id TEXT PRIMARY KEY REFERENCES catalog_items ON DELETE CASCADE,main_story_minutes INTEGER NULL CHECK(main_story_minutes IS NULL OR main_story_minutes>=0),main_extra_minutes INTEGER NULL CHECK(main_extra_minutes IS NULL OR main_extra_minutes>=0),completionist_minutes INTEGER NULL CHECK(completionist_minutes IS NULL OR completionist_minutes>=0),source_name TEXT NULL,observed_at TEXT NULL,revision INTEGER NOT NULL DEFAULT 1);
CREATE TABLE catalog_sources(source_id TEXT PRIMARY KEY,source_group TEXT NOT NULL,source_name TEXT NOT NULL,source_url TEXT NULL,retrieved_at TEXT NOT NULL);
CREATE TABLE catalog_field_sources(catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,field_path TEXT NOT NULL,source_id TEXT NOT NULL REFERENCES catalog_sources,confidence REAL NULL,PRIMARY KEY(catalog_id,field_path,source_id));
CREATE TABLE catalog_images(image_id TEXT PRIMARY KEY,catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,image_role TEXT NOT NULL CHECK(image_role IN ('cover','background','logo')),variant TEXT NOT NULL CHECK(variant IN ('thumb','list','quick','cover')),relative_path TEXT NOT NULL UNIQUE,width INTEGER NOT NULL CHECK(width>0),height INTEGER NOT NULL CHECK(height>0),format TEXT NOT NULL,checksum_sha256 TEXT NOT NULL,is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN(0,1)),revision INTEGER NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX uq_catalog_image_primary ON catalog_images(catalog_id,image_role,variant) WHERE is_primary=1;
CREATE TABLE catalog_payloads(catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,payload_type TEXT NOT NULL,payload_version INTEGER NOT NULL,payload_json TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(catalog_id,payload_type));
CREATE TABLE catalog_editions(edition_id TEXT PRIMARY KEY,catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,canonical_name TEXT NOT NULL,display_name TEXT NOT NULL,edition_type TEXT NOT NULL CHECK(edition_type IN ('standard','deluxe','collectors','complete','platform','regional','other')),release_id TEXT NULL REFERENCES releases ON DELETE SET NULL,description TEXT NULL,is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN(0,1)),revision INTEGER NOT NULL DEFAULT 1,UNIQUE(catalog_id,canonical_name COLLATE NOCASE));
CREATE UNIQUE INDEX uq_catalog_primary_edition ON catalog_editions(catalog_id) WHERE is_primary=1;
CREATE TABLE catalog_addons(addon_id TEXT PRIMARY KEY,parent_catalog_id TEXT NOT NULL REFERENCES catalog_items ON DELETE CASCADE,addon_catalog_id TEXT NULL REFERENCES catalog_items ON DELETE SET NULL,canonical_name TEXT NOT NULL,display_name TEXT NOT NULL,addon_type TEXT NOT NULL CHECK(addon_type IN ('dlc','expansion','season_pass','content_pack','soundtrack','other')),release_date TEXT NULL,description TEXT NULL,revision INTEGER NOT NULL DEFAULT 1,UNIQUE(parent_catalog_id,canonical_name COLLATE NOCASE));
CREATE TABLE catalog_search_documents(rowid INTEGER PRIMARY KEY,catalog_id TEXT NOT NULL UNIQUE,normalized_text TEXT NOT NULL,display_title TEXT NOT NULL);
CREATE VIRTUAL TABLE catalog_fts USING fts5(normalized_text,display_title,content='catalog_search_documents',content_rowid='rowid',tokenize='unicode61 remove_diacritics 2');
CREATE TABLE migration_history(migration_id TEXT PRIMARY KEY,from_version INTEGER NOT NULL,to_version INTEGER NOT NULL,checksum_sha256 TEXT NOT NULL,app_version TEXT NOT NULL,backup_snapshot_id TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT NULL,finished_at TEXT NULL,status TEXT NOT NULL CHECK(status IN ('prepared','running','committed','verified','restored','failed')),error_text TEXT NULL,diagnostic TEXT NULL);
CREATE UNIQUE INDEX uq_migration_verified_target ON migration_history(to_version) WHERE status='verified';
CREATE TABLE patch_history(patch_id TEXT PRIMARY KEY,manifest_sha256 TEXT NOT NULL,from_catalog_version TEXT NOT NULL,to_catalog_version TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT NULL,status TEXT NOT NULL CHECK(status IN ('running','finalized','failed','rolled_back')),result_json TEXT NULL);
CREATE TABLE patch_runs(patch_id TEXT PRIMARY KEY REFERENCES patch_history,state TEXT NOT NULL CHECK(state IN ('staged','verified','db_prepared','db_committed','media_activated','finalized','failed')),last_safe_state TEXT NULL,work_dir TEXT NOT NULL,snapshot_id TEXT NULL,pending_catalog_version TEXT NULL,pending_media_version TEXT NULL,old_media_version TEXT NULL,diagnostic TEXT NULL,updated_at TEXT NOT NULL);
CREATE TABLE catalog_runtime_state(singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),active_catalog_version TEXT NOT NULL,active_media_version TEXT NOT NULL,pending_catalog_version TEXT NULL,pending_media_version TEXT NULL,contracts_version INTEGER NOT NULL,patch_format_version INTEGER NOT NULL,updated_at TEXT NOT NULL);
"""

USER_SCHEMA = """
CREATE TABLE schema_meta(singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),schema_version INTEGER NOT NULL,contract_version INTEGER NOT NULL,core_generation INTEGER NOT NULL,reset_boundary TEXT NULL,reset_operation_id TEXT NULL,reset_state TEXT NULL CHECK(reset_state IN ('completed')),reset_started_at TEXT NULL,reset_completed_at TEXT NULL,updated_at TEXT NOT NULL);
CREATE TABLE user_items(user_item_id TEXT PRIMARY KEY,media_type TEXT NOT NULL CHECK(media_type IN ('game','film','series','program')),title TEXT NOT NULL,release_year INTEGER NULL,description TEXT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,is_archived INTEGER NOT NULL DEFAULT 0 CHECK(is_archived IN(0,1)));
CREATE TABLE user_item_links(user_item_id TEXT PRIMARY KEY REFERENCES user_items ON DELETE CASCADE,catalog_id TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','inactive')),linked_at TEXT NOT NULL,unlinked_at TEXT NULL);
CREATE TABLE user_library_state(source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,membership_state TEXT NOT NULL DEFAULT 'active' CHECK(membership_state IN ('active','archived')),favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN(0,1)),projected_status TEXT NULL,projected_progress_value REAL NULL,projected_progress_unit TEXT NULL,projected_total_playtime_minutes INTEGER NOT NULL DEFAULT 0 CHECK(projected_total_playtime_minutes>=0),started_at TEXT NULL,completed_at TEXT NULL,archived_at TEXT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(source_type,item_id));
CREATE TABLE playthroughs(playthrough_id TEXT PRIMARY KEY,source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,sequence_no INTEGER NOT NULL CHECK(sequence_no>0),status TEXT NOT NULL CHECK(status IN ('planned','playing','completed','abandoned')),started_at TEXT NULL,ended_at TEXT NULL,playtime_minutes INTEGER NOT NULL DEFAULT 0 CHECK(playtime_minutes>=0),progress_value REAL NULL,progress_unit TEXT NULL,is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN(0,1)),deleted_at TEXT NULL,UNIQUE(source_type,item_id,sequence_no));
CREATE UNIQUE INDEX uq_current_playthrough ON playthroughs(source_type,item_id) WHERE is_current=1 AND deleted_at IS NULL;
CREATE TABLE user_ratings(rating_id TEXT PRIMARY KEY,source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,playthrough_id TEXT NULL REFERENCES playthroughs ON DELETE SET NULL,rating_type TEXT NOT NULL CHECK(rating_type IN ('checkpoint','final')),checkpoint_type TEXT NULL CHECK(checkpoint_type IN ('start','middle','end')),value_tenths INTEGER NULL CHECK(value_tenths BETWEEN 0 AND 100),review_text TEXT NULL,is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN(0,1)),superseded_at TEXT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,CHECK((rating_type='checkpoint' AND playthrough_id IS NOT NULL AND checkpoint_type IS NOT NULL) OR (rating_type='final' AND checkpoint_type IS NULL)),CHECK(rating_type<>'final' OR value_tenths IS NOT NULL));
CREATE UNIQUE INDEX uq_current_checkpoint_rating ON user_ratings(playthrough_id,checkpoint_type) WHERE rating_type='checkpoint' AND is_current=1;
CREATE UNIQUE INDEX uq_current_final_rating ON user_ratings(source_type,item_id) WHERE rating_type='final' AND is_current=1;
CREATE INDEX ix_rating_history_item ON user_ratings(source_type,item_id,created_at);
CREATE TABLE rating_criteria(criterion_rating_id TEXT PRIMARY KEY,rating_id TEXT NOT NULL REFERENCES user_ratings ON DELETE CASCADE,criterion_code TEXT NOT NULL,value_tenths INTEGER NOT NULL CHECK(value_tenths BETWEEN 0 AND 100),UNIQUE(rating_id,criterion_code));
CREATE TABLE impressions(impression_id TEXT PRIMARY KEY,playthrough_id TEXT NOT NULL REFERENCES playthroughs ON DELETE CASCADE,checkpoint_type TEXT NULL CHECK(checkpoint_type IN ('start','middle','end')),text TEXT NOT NULL,progress_value REAL NULL,progress_unit TEXT NULL,playtime_minutes_at_entry INTEGER NULL CHECK(playtime_minutes_at_entry IS NULL OR playtime_minutes_at_entry>=0),created_at TEXT NOT NULL);
CREATE UNIQUE INDEX uq_checkpoint_impression ON impressions(playthrough_id,checkpoint_type) WHERE checkpoint_type IS NOT NULL;
CREATE TABLE journey_events(event_id TEXT PRIMARY KEY,operation_id TEXT NOT NULL UNIQUE,source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,playthrough_id TEXT NULL REFERENCES playthroughs ON DELETE SET NULL,event_type TEXT NOT NULL,payload_version INTEGER NOT NULL DEFAULT 1,payload_json TEXT NOT NULL,occurred_at TEXT NOT NULL);
CREATE INDEX ix_journey_item_time ON journey_events(source_type,item_id,occurred_at); CREATE INDEX ix_journey_playthrough_time ON journey_events(playthrough_id,occurred_at);
CREATE TABLE user_notes(source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,text TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(source_type,item_id));
CREATE TABLE user_taxonomy_nodes(node_id TEXT PRIMARY KEY,parent_id TEXT NULL REFERENCES user_taxonomy_nodes ON DELETE RESTRICT,node_type TEXT NOT NULL CHECK(node_type IN ('category','subcategory','tag')),name TEXT NOT NULL,sort_order INTEGER NOT NULL DEFAULT 0,is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)));
CREATE UNIQUE INDEX uq_taxonomy_root_name ON user_taxonomy_nodes(node_type,name COLLATE NOCASE) WHERE parent_id IS NULL;
CREATE UNIQUE INDEX uq_taxonomy_child_name ON user_taxonomy_nodes(parent_id,node_type,name COLLATE NOCASE) WHERE parent_id IS NOT NULL;
CREATE TABLE user_item_taxonomy(source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,node_id TEXT NOT NULL REFERENCES user_taxonomy_nodes ON DELETE CASCADE,PRIMARY KEY(source_type,item_id,node_id));
CREATE TABLE user_game_metrics(metric_id TEXT PRIMARY KEY,source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,metric_code TEXT NOT NULL CHECK(metric_code IN ('battle_royale_matches','battle_royale_first_places')),period_key TEXT NOT NULL DEFAULT 'lifetime',value REAL NOT NULL CHECK(value>=0),updated_at TEXT NOT NULL,UNIQUE(source_type,item_id,metric_code,period_key));
CREATE TABLE achievement_definitions(achievement_id TEXT PRIMARY KEY,code TEXT NOT NULL UNIQUE,title TEXT NOT NULL,description TEXT NOT NULL,rule_type TEXT NOT NULL,rule_json TEXT NOT NULL,icon_key TEXT NOT NULL,is_hidden INTEGER NOT NULL DEFAULT 0 CHECK(is_hidden IN(0,1)),is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN(0,1)));
CREATE TABLE user_achievements(achievement_id TEXT PRIMARY KEY REFERENCES achievement_definitions,unlocked_at TEXT NULL,progress_value REAL NOT NULL DEFAULT 0,progress_target REAL NULL,evaluation_key TEXT NULL,source_operation_id TEXT NULL);
CREATE UNIQUE INDEX uq_achievement_evaluation_key ON user_achievements(evaluation_key) WHERE evaluation_key IS NOT NULL;
CREATE TABLE achievement_evaluations(evaluation_key TEXT PRIMARY KEY,achievement_id TEXT NOT NULL REFERENCES achievement_definitions,triggering_event_id TEXT NOT NULL,evaluated_at TEXT NOT NULL,result_code TEXT NOT NULL,UNIQUE(achievement_id,triggering_event_id));
CREATE TABLE statistics_cache(cache_key TEXT PRIMARY KEY,cache_version INTEGER NOT NULL,payload_json TEXT NOT NULL,generated_at TEXT NOT NULL,invalidated_at TEXT NULL);
CREATE TABLE user_media(user_media_id TEXT PRIMARY KEY,source_type TEXT NOT NULL CHECK(source_type IN ('official','user')),item_id TEXT NOT NULL,media_role TEXT NOT NULL CHECK(media_role IN ('custom_cover','screenshot','attachment','export_source')),relative_path TEXT NOT NULL UNIQUE,mime_type TEXT NOT NULL,width INTEGER NULL,height INTEGER NULL,checksum_sha256 TEXT NOT NULL,is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN(0,1)),created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE UNIQUE INDEX uq_user_primary_cover ON user_media(source_type,item_id) WHERE media_role='custom_cover' AND is_primary=1;
CREATE TABLE user_search_documents(rowid INTEGER PRIMARY KEY,user_item_id TEXT NOT NULL UNIQUE,normalized_text TEXT NOT NULL,display_title TEXT NOT NULL);
CREATE VIRTUAL TABLE user_fts USING fts5(normalized_text,display_title,content='user_search_documents',content_rowid='rowid',tokenize='unicode61 remove_diacritics 2');
CREATE TABLE app_settings(key TEXT PRIMARY KEY,value_json TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE migration_history(migration_id TEXT PRIMARY KEY,from_version INTEGER NOT NULL,to_version INTEGER NOT NULL,checksum_sha256 TEXT NOT NULL,app_version TEXT NOT NULL,backup_snapshot_id TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT NULL,finished_at TEXT NULL,status TEXT NOT NULL CHECK(status IN ('prepared','running','committed','verified','restored','failed')),error_text TEXT NULL,diagnostic TEXT NULL);
CREATE UNIQUE INDEX uq_migration_verified_target ON migration_history(to_version) WHERE status='verified';
CREATE TABLE snapshot_registry(snapshot_id TEXT PRIMARY KEY,snapshot_type TEXT NOT NULL CHECK(snapshot_type IN ('legacy_reset','pre_migration','manual','pre_restore')),database_path TEXT NOT NULL,media_path TEXT NULL,manifest_path TEXT NOT NULL,checksum_sha256 TEXT NOT NULL,created_at TEXT NOT NULL,verified_at TEXT NULL,status TEXT NOT NULL CHECK(status IN ('created','verified','invalid','restored')));
"""


class SchemaManager:
    def __init__(self, policy: SQLitePolicy | None = None) -> None:
        self.policy = policy or SQLitePolicy()

    def _create(self, path: Path, script: str, *, kind: str, operation_id: str | None) -> None:
        path = Path(path)
        if path.exists() and path.stat().st_size:
            raise ValidationError(f"Refusing to create {kind} schema over an existing database")
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = self.policy.connect(path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(script)
            now = utc_now()
            connection.execute(
                "INSERT INTO schema_meta VALUES(1,?,?,?,?,?,?,?)"
                if kind == "catalog"
                else "INSERT INTO schema_meta VALUES(1,?,?,?,?,?,?,?,?,?)",
                (
                    SCHEMA_VERSION,
                    CONTRACT_VERSION,
                    CORE_GENERATION,
                    RESET_BOUNDARY if kind == "user" else None,
                    operation_id if kind == "user" else None,
                    "completed" if kind == "user" else None,
                    now,
                )
                if kind == "catalog"
                else (
                    SCHEMA_VERSION,
                    CONTRACT_VERSION,
                    CORE_GENERATION,
                    RESET_BOUNDARY,
                    operation_id,
                    "completed",
                    now,
                    now,
                    now,
                ),
            )
            if kind == "catalog":
                connection.execute(
                    "INSERT INTO catalog_runtime_state VALUES(1,?,?,?,?,?,?,?)",
                    (CATALOG_VERSION, CATALOG_VERSION, None, None, CONTRACT_VERSION, 1, now),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            connection.close()
            path.unlink(missing_ok=True)
            raise
        finally:
            if connection:
                connection.close()
        self.validate(path, expected_operation_id=operation_id if kind == "user" else None)

    def create_catalog(self, path: Path) -> None:
        self._create(path, CATALOG_SCHEMA, kind="catalog", operation_id=None)

    def create_user(self, path: Path, *, reset_operation_id: str | None = None) -> None:
        self._create(path, USER_SCHEMA, kind="user", operation_id=reset_operation_id)

    def validate(self, path: Path, *, expected_operation_id: str | None = None) -> None:
        connection = self.policy.connect(path, read_only=True)
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise IntegrityError("SQLite integrity_check failed")
            if list(connection.execute("PRAGMA foreign_key_check")):
                raise IntegrityError("SQLite foreign_key_check failed")
            row = connection.execute("SELECT * FROM schema_meta").fetchone()
            if row is None or connection.execute("SELECT COUNT(*) FROM schema_meta").fetchone()[0] != 1:
                raise IntegrityError("schema_meta must contain exactly one row")
            if (row["schema_version"], row["contract_version"], row["core_generation"]) != (1, 1, 1):
                raise IntegrityError("Database schema/core generation is incompatible")
            if expected_operation_id is not None and row["reset_operation_id"] != expected_operation_id:
                raise IntegrityError("Reset operation ID does not match generation")
        finally:
            connection.close()
