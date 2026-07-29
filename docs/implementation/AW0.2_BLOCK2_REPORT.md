# AW0.2 Block 2 Report

Implementation status: **complete** for the requested combined storage block
(Implementation Plan Blocks 2 and 3 foundations).

## Scope completed

- Frozen Schema 1 creators for `catalog.db` and `user.db`.
- Schema metadata, Core Generation 1 and reset-boundary metadata.
- External-content FTS5 document/index tables without startup triggers.
- Typed catalog/user SQLite sessions with explicit transaction ownership.
- Catalog and user Units of Work; no cross-database transaction.
- Typed repositories for catalog items, user items, library projection,
  playthroughs, Journey, ratings, impressions and system metadata.
- Read-only contiguous migration discovery with SHA-256 checksums.
- External, durable AW0.2 one-time reset state machine.
- Snapshot-backed reset, generation quarantine and atomic generation pointer.
- Storage/repository/reset smoke and fault-injection tests.

## Files added

- `app/storage/models.py`
- `app/storage/schema.py`
- `app/storage/repositories.py`
- `app/storage/unit_of_work.py`
- `app/storage/migrations.py`
- `app/storage/reset.py`
- `tests/test_aw02_schema_and_repositories.py`
- `tests/test_aw02_reset.py`
- `tests/test_aw02_migration_discovery.py`
- `docs/implementation/AW0.2_BLOCK2_REPORT.md`

## Files changed

- `app/core/paths.py` — added generation, quarantine and active-pointer paths.
- `app/storage/sqlite_policy.py` — added typed catalog/user transaction sessions.
- `app/storage/__init__.py` — exported the new storage contracts.
- `docs/implementation/AW0.2_NEXT_BLOCK.md` — advanced the authorized next block.

No AW0.1 UI module or existing user database was connected, modified or reset.

## Created catalog.db tables

`schema_meta`, `catalog_items`, `catalog_external_ids`, `catalog_titles`,
`companies`, `company_roles`, `platforms`, `releases`,
`catalog_companies`, `genres`, `tags`, `catalog_genres`, `catalog_tags`,
`relations`, `catalog_redirects`, `catalog_ratings`, `game_duration`,
`catalog_sources`, `catalog_field_sources`, `catalog_images`,
`catalog_payloads`, `catalog_editions`, `catalog_addons`,
`catalog_search_documents`, `catalog_fts`, `migration_history`,
`patch_history`, `patch_runs`, `catalog_runtime_state`.

## Created user.db tables

`schema_meta`, `user_items`, `user_item_links`, `user_library_state`,
`playthroughs`, `user_ratings`, `rating_criteria`, `impressions`,
`journey_events`, `user_notes`, `user_taxonomy_nodes`,
`user_item_taxonomy`, `user_game_metrics`, `achievement_definitions`,
`user_achievements`, `achievement_evaluations`, `statistics_cache`,
`user_media`, `user_search_documents`, `user_fts`, `app_settings`,
`migration_history`, `snapshot_registry`.

## Repository contracts

- `CatalogRepository`: add/get/list typed official catalog items.
- `UserItemRepository`: add/get typed user-owned items.
- `LibraryRepository`: upsert/get the service-owned library projection.
- `PlaythroughRepository`: add/get/update typed playthrough state.
- `JourneyRepository`: append and query typed, operation-idempotent events.
- `RatingRepository`: append rating history and query current final rating.
- `ImpressionRepository`: append/get typed impressions.
- `SystemStateRepository`: read typed Schema/Core metadata.

Repositories only issue SQL. They do not commit, return `sqlite3.Row`, import
Qt/UI code or coordinate two databases.

## Reset state machine

External authority is `profile/reset_state.json`:

```text
legacy_detected
→ snapshot_verified
→ legacy_archived
→ schema_created
→ completed
```

Every transition checks its postcondition before advancing. A verified
Snapshot Foundation snapshot is mandatory before the legacy database/media
are atomically archived. A matching archive or generation is reused.
Partial expected generations are moved to `profile/quarantine`; a generation
owned by another operation, a checksum mismatch, both source/archive present
or neither present causes a hard stop. Activation writes
`profile/active_generation.json` atomically. A completed journal is terminal
and makes subsequent launches non-destructive.

## End-to-end transaction smoke result

Passed:

1. created clean catalog/user Schema 1 databases;
2. verified metadata, integrity, foreign keys and FTS tables;
3. inserted and re-read a typed catalog item;
4. inserted a user item;
5. created library projection and playthrough;
6. wrote Journey, rating and impression data;
7. restarted the storage layer and re-read typed values;
8. injected a failure after projection/playthrough writes;
9. verified rollback left neither partial row.

## Verification

```text
python -m unittest tests.test_aw02_schema_and_repositories \
  tests.test_aw02_reset tests.test_aw02_migration_discovery -v
python -m unittest discover -s tests -v
python -m compileall -q app velora_contracts tests
git diff --check
```

Results:

- New Block 2 tests: **14 passed**.
- Full regression suite: **81 passed**.
- Compile check: **passed**.
- Diff whitespace check: **passed** (Git only reports expected Windows
  LF-to-CRLF conversion notice).
- No UI/PySide dependency in contracts/storage foundation: **passed**.

## Safety statement

All destructive reset tests used `TemporaryDirectory`. No current Velora
profile, `catalog.db`, `user.db` or media directory was changed.

## Deferred

No core application services, search engine, patch application, full
migration execution/recovery, Games UI, other media types, analytics,
achievements, export, executable or installer was implemented.
