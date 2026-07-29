# AW0.2 Block 3 Report

## Scope

Block 3 implements the Games Core Vertical Smoke Slice without connecting it
to the AW0.1 UI. The slice uses Schema 1, typed repositories and explicit
database-specific Units of Work.

## Implemented application services

- `LibraryService.add`
- `PlaythroughService.create`
- `PlaythroughService.start`
- `PlaythroughService.set_status`
- `PlaythroughService.add_playtime`
- `GameProgressService.create_checkpoint`
- `ImpressionService.create`
- `RatingService.save_checkpoint`
- `RatingService.save_final`
- `JourneyService.list_for_game`
- `JourneyService.get_game_row`

All service inputs and outputs are typed domain/storage models. No service
returns `sqlite3.Row`, imports PySide6 or imports an UI module.

## Read model

`GameRowReadModel` is a UI-independent projection for a future Games catalog
row. It contains `user_item_id`, `catalog_item_ref`, `title`,
`library_lifecycle_state`, `current_playthrough_id`, `playthrough_status`,
`total_playtime_minutes`, `current_checkpoint`,
`current_personal_rating_tenths`, `latest_impression_preview` and
`updated_at`.

Time and rating values stay canonical integers. The application layer does not
apply display formatting.

## Transaction boundaries

Each command opens exactly one `UserUnitOfWork` and commits only through that
Unit of Work:

- adding a library item writes its projection and `library_added` Journey
  event together;
- creating a playthrough writes the playthrough, library projection and
  `playthrough_started` Journey event together;
- changing status writes the playthrough, library projection and status
  Journey event together;
- adding playtime writes authoritative time, its projection and
  `playtime_added` together;
- creating a checkpoint writes its projection and `milestone_recorded`
  together;
- adding an impression writes it and `impression_added` together;
- saving a rating supersedes the previous current rating, inserts the new
  immutable history row and writes `rating_changed` together.

No command combines `catalog.db` and `user.db` in one SQLite transaction.
Catalog references are verified before the user transaction. Post-commit
events are dispatched only after successful commit; rollback publishes none.

## Full smoke Journey

The tested full playthrough produces this immutable order:

1. `library_added`
2. `playthrough_started`
3. `status_changed`
4. `playtime_added`
5. `milestone_recorded`
6. `impression_added`
7. `rating_changed` (checkpoint)
8. `playthrough_completed`
9. `rating_changed` (final)

Ordering is defined by `occurred_at`, then `created_at`, then stable event ID.

## Validation

- Block 3 tests: **15/15 passed**
- Full regression suite: **96/96 passed**
- `compileall`: **success**
- Atomic rollback: **passed**
- Post-commit suppression on rollback: **passed**
- Storage reopen and persistence: **passed**
- UI/PySide6 dependency scan: **passed**

The required scenario was executed from catalog lookup through final rating,
read model construction, Journey readback and storage-layer restart.

## Explicit exclusions

This block does not implement or connect Games UI, search, images, catalog
relations, achievements, analytics, export, other media types, patch apply,
the full migration engine, executable packaging or installation.

