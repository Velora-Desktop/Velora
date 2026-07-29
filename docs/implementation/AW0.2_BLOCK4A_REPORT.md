# AW0.2 Block 4A Report

## Scope

Block 4A prepares the read-side and adapter boundary for one future Games row.
It does not modify or connect the existing Games UI.

## Public query API

`GamesRowQueryService` exposes:

- `list_game_rows(filters, sort, pagination)`
- `get_game_row(ref)`
- `refresh_game_row(ref)`
- `resolve_row_actions(row)`
- `get_row_state(ref)`

All APIs return immutable typed contracts. The facade imports no PySide6,
QWidget, QObject, Qt model or existing UI module.

## Typed contracts

### Filtering

`GameRowFilter` supports:

- `lifecycle_state`
- `playthrough_status`
- `has_rating`
- `has_active_playthrough`

### Sorting

`GameRowSort` combines:

- field: `updated_at`, `title`, `personal_rating`, `total_playtime`
- direction: `ascending`, `descending`

Every sort begins from the stable identity order
`source_type + item_id`. Equal values therefore keep deterministic order.
Missing optional values are placed after present values.

### Pagination

- `PageRequest`: `page`, `page_size`
- `PageInfo`: `page`, `page_size`, `total_items`, `total_pages`

Pagination is applied only after filtering and stable sorting.

### Row and selection

`GameRowDto` is a UI-neutral mapping of `GameRowReadModel`.
`RowSelectionIdentity` contains immutable `source_type` and `item_id`, with a
stable key that does not depend on title or row position.

### State

`GameRowsState` and `GameRowState` support:

- `loading`
- `empty`
- `error`
- `result`

Domain failures are mapped to `QueryError(code, message)`. No raw storage
exception or database row is part of the public result contract.

## Row action rules

Actions are derived from current domain state:

- no playthrough / planned: `open`, `start_playthrough`;
- playing: `open`, `continue_playthrough`, `add_playtime`,
  `add_checkpoint`, `add_impression`, `rate`, `complete_playthrough`;
- completed / abandoned: `open`, `start_playthrough`, `add_impression`,
  `rate`.

Actions are not persisted as UI flags.

## Read-only boundary

- list and single-row queries perform no writes;
- no user entity is created by a query;
- refresh performs a fresh read and has no cache mutation;
- repositories remain hidden behind the application facade;
- no display colors, icons, dimensions or localized formatting are produced.

## Validation

- Block 4A focused tests: **20/20 passed**
- Full regression suite: **116/116 passed**
- `compileall`: **success**
- UI/PySide6 import boundary: **passed**
- stable order and page uniqueness: **passed**
- typed error state: **passed**

## Explicit exclusions

No existing row widget, Qt model, search engine, image service, relations,
analytics, export, other content module, patch engine or packaging code was
implemented or changed.

