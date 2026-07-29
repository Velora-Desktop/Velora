# AW0.2 Block 4B Report

## Scope

Block 4B connects exactly one existing Games row to the AW0.2 read-only
facade. It does not migrate the rest of the list and does not connect any
write command.

## Integrated row

- visible legacy row: `Doom Eternal`
- legacy catalog ID used only to locate the existing widget:
  `g-shooter-fps-002`
- Contracts 1 selection/catalog UUID:
  `9df7cc01-d487-4cd7-814d-e70ec7967a4a`

The adapter keeps these identities separate. The legacy readable ID is never
passed to `CatalogItemRef`, whose normative identity remains UUID-based.

## Data path

```text
GamesRowQueryService
-> GameRowState / GameRowDto
-> SingleGameRowViewModel
-> GameRowPresentation
-> SingleGameRowPresenter
-> existing GameRow widget
```

The widget never accesses SQLite or repositories. Application filtering,
selection identity and action calculation are not copied into QWidget code.

## Rendering

The presenter maps only values already supported by the existing row:

- title;
- playthrough status;
- personal rating.

Lifecycle, total playtime, checkpoint, impression preview and `updated_at`
remain available in the ViewModel presentation but are not added as new
visible fields.

Missing rating is rendered as `—`. Missing playthrough uses the existing
`НЕ НАЧИНАЛ` status. Loading temporarily disables the same row without
changing its geometry. A typed error keeps the legacy content visible and
stores the error in the row tooltip instead of closing the screen.

## Refresh and selection

`CatalogView.refresh_integrated_row(...)` finds the already existing target
widget and applies a fresh DTO to it. It does not rebuild the list, replace
other widgets or run sorting. `RowSelectionIdentity` is therefore preserved
across refresh and other row order cannot change.

## Read-only actions

Allowed actions are obtained only from
`GamesRowQueryService.resolve_row_actions(...)` and retained on the row as
`aw02_available_actions`.

For this block the legacy status and rating write controls on the integrated
row are disabled. No old write handler is redirected to the new core and no
new write service is invoked.

## Feature flag and rollback

The integration is disabled by default.

Enable:

```text
VELORA_AW02_SINGLE_ROW_READ=1
```

Optional test/override values:

```text
VELORA_AW02_SINGLE_ROW_ID=<AW0.2 catalog UUID>
VELORA_AW02_SINGLE_ROW_LEGACY_ID=<legacy widget catalog ID>
```

Rollback requires removing or setting
`VELORA_AW02_SINGLE_ROW_READ=0`. `build_single_row_presenter()` then returns
`None` and the catalog follows the unchanged legacy path.

## Visual differences

No layout, dimensions, colors, columns or global navigation were changed.
When the feature is enabled:

- status and personal-rating controls of the single target row are disabled
  because Block 4B is read-only;
- loading and error information is exposed through enabled state/tooltips,
  without a new panel or redesigned row.

All other rows retain their previous behavior and appearance.

## Validation

- Block 4B integration tests: **12/12 passed**
- full regression suite: **128/128 passed**
- `compileall`: **success**
- `git diff --check`: **success**
- direct SQLite access from integration UI: **absent**
- repository imports from integration UI: **absent**
- feature-flag rollback: **passed**

