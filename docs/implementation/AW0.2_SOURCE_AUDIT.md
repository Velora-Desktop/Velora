# AW0.2 Source Audit

Status: completed for Gate 1 and limited to the Block 1 implementation surface.

## Current source map

- `main.py`, `app/ui`, `app/styles`, `assets`: working AW0.1 presentation layer.
- `app/models`: prototype UI-facing records.
- `app/data`: existing catalog and user repositories.
- `app/database`: experimental migration runner and SQL migrations.
- `app/services`: existing application/UI coordination services.
- `app/core`: paths, constants, icon registry and display helpers.
- `tests`: unittest-based regression suite.
- `C:\Velora studio\studio\database`, `studio/services`, `studio/ui`: separate Studio layers.

## Reusable modules

- `app/core/paths.py`: retained as the compatibility import surface and extended
  through `AppPaths`.
- Existing SQLite repositories and migration scripts remain available for the
  later file-by-file Block 2/3 migration; they are not reused as Contracts 1
  foundations because their schema and transaction model are experimental.
- Existing `unittest` infrastructure is reused.
- Existing UI, theme, navigation, icon and visual assets remain untouched.

## Prototype code to quarantine or replace later

- `app/models/game.py` is a presentation-era aggregate and is not a shared
  contract. Games ViewModels may adapt it after Blocks 1–4.
- `app/database/migration_runner.py` predates Migration Protocol v1.1. It must
  not execute Schema 1 migrations until replaced/adapted in Block 2.
- `app/services/data_backup_service.py` is Qt-coupled and implements the
  experimental backup format. It remains available to AW0.1 but is not the
  Backup Protocol v1.1 foundation.
- Existing repositories open/own connections inconsistently. They remain
  untouched until the typed repository/session work in Block 3.

No files were deleted.

## Direct frozen-contract violations identified

1. The previous path module exposed only a small set of directories and had no
   profile, staging, snapshot or recovery-journal paths.
2. There was no UI-independent Contracts 1 package.
3. There was no common SQLite policy enforcing foreign keys, busy timeout and
   explicit service-owned transaction boundaries.
4. Existing backup code depends on PySide6 and cannot be used before first-run
   UI/reset.
5. Patch JSON/checksum validation and atomic external recovery journals were
   absent.

These violations are addressed additively by the Block 1 patch. Existing AW0.1
runtime behavior is not redirected to unfinished AW0.2 engines.

## File-by-file migration plan

- `velora_contracts/*`: stable content-neutral contracts shared later with
  Studio.
- `app/core/paths.py`: compatibility facade over the new `AppPaths`.
- `app/storage/sqlite_policy.py`: base for typed `UserDbSession` and
  `CatalogDbSession` in Block 3.
- `app/storage/snapshots.py`: verified primitive used by reset and migration
  implementations in Block 2.
- `app/storage/recovery.py`: durable journal primitive used by later reset,
  migration, patch and restore state machines.
- `app/database/*`: replace/adapt only in Block 2 after Schema 1 creators exist.
- `app/data/*`: migrate to typed repositories in Block 3.
- `app/services/*`: migrate lifecycle/playthrough/rating/Journey orchestration
  in Block 4.
- `app/ui/*`: keep unchanged until the Block 6 Games render gate.

## Tests

Existing tests cover AW0.1 UI/catalog behavior. Block 1 adds:

- contract and event serialization round trips;
- typed ID and closed-event rejection;
- canonical JSON and published SHA-256 fixture;
- package path, checksum, manifest, media and operation validation;
- `AppPaths`;
- SQLite foreign-key/busy-timeout/rollback policy;
- atomic JSON recovery journal;
- snapshot creation, verification and source preservation after failure;
- import-boundary guard against PySide/UI dependencies.

Later blocks must add Schema 1 creation/reset interruption tests, typed
repository tests and the first atomic playthrough/projection/Journey test.
