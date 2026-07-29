# AW0.2 Block 4B Verification Report

## Scope

This verification stage proves the opt-in, read-only data path for the
existing Doom Eternal row only:

`GamesRowQueryService`
→ `GameRowState` / `GameRowDto`
→ `SingleGameRowViewModel`
→ `GameRowPresentation`
→ `SingleGameRowPresenter`
→ existing `GameRow`.

No other row, write action, schema, repository contract, navigation flow, or
global Games UI component was connected.

## Feature flags

- `VELORA_AW02_SINGLE_ROW_READ=1` creates the presenter when `CatalogView` is
  constructed at application startup.
- `VELORA_AW02_SINGLE_ROW_READ=0`, an empty value, or a missing variable keeps
  the legacy path and creates no presenter.
- `VELORA_AW02_SINGLE_ROW_DIAGNOSTIC=1` changes only the presentation value of
  the Doom Eternal personal rating to `8.7 AW02`.
- Both flags are read once while their related UI integration objects are
  constructed. Restart Velora after changing a flag.

PowerShell command for the VS Code terminal:

```powershell
$env:VELORA_AW02_SINGLE_ROW_READ="1"
$env:VELORA_AW02_SINGLE_ROW_DIAGNOSTIC="1"
& "C:\Program Files\Python312\python.exe" "C:\Velora\main.py"
```

To return to the untouched legacy path:

```powershell
Remove-Item Env:VELORA_AW02_SINGLE_ROW_READ -ErrorAction SilentlyContinue
Remove-Item Env:VELORA_AW02_SINGLE_ROW_DIAGNOSTIC -ErrorAction SilentlyContinue
& "C:\Program Files\Python312\python.exe" "C:\Velora\main.py"
```

The successful manual render requires valid Schema 1 databases at:

- `%LOCALAPPDATA%\Velora\data\catalog.db`;
- `%LOCALAPPDATA%\Velora\data\user.db`.

The verification code deliberately does not create, migrate, seed, or alter
these databases from the UI. If they are absent or do not contain the
Contracts UUID, the typed fail-safe path is expected: the legacy row remains
visible, no success marker appears, and the console contains an AW0.2 error.

## Runtime proof

Presenter construction:

```text
[AW0.2][SingleRow] attached
legacy_id=g-shooter-fps-002
contracts_id=9df7cc01-d487-4cd7-814d-e70ec7967a4a
```

Successful DTO render:

```text
[AW0.2][SingleRow] rendered from GameRowDto
title=Doom Eternal
selection_identity=official:9df7cc01-d487-4cd7-814d-e70ec7967a4a
state=result
```

Successful targeted refresh:

```text
[AW0.2][SingleRow] refreshed
contracts_id=9df7cc01-d487-4cd7-814d-e70ec7967a4a
```

Failures use a typed, sanitized diagnostic:

```text
[AW0.2][SingleRow] error
code=<typed error code>
message=<single-line error message>
```

No DTO dump, database contents, or personal profile data is logged.

## Visible marker

After a successful `GameRowDto` render, the existing Doom Eternal title field
shows:

`Doom Eternal · AW0.2 READ`

The marker is produced only by `SingleGameRowPresenter`. It adds no widget and
does not change row geometry. Other games never receive it. An error restores
the captured legacy title, rating, status, tooltips, and enabled states, and
clears the marker.

## Diagnostic override safety

`VELORA_AW02_SINGLE_ROW_DIAGNOSTIC=1` changes only
`GameRowPresentation.personal_rating`. It does not mutate `GameRowDto`, execute
a service write, or modify either SQLite file. Automated verification compares
both database files byte-for-byte before and after the override render.

## Automated verification

Focused tests:

```text
python -m unittest tests.test_aw02_single_game_row_ui -v
Ran 18 tests
OK
```

Covered behavior:

- feature flag on, off, and absent;
- exact Doom Eternal Contracts UUID;
- no attachment to another row;
- successful marker and error-state marker suppression;
- legacy restoration after a typed read failure;
- diagnostic override without database changes;
- targeted refresh diagnostic event;
- stable selection and unchanged row ordering;
- no direct SQLite or repository imports in the UI adapter.

Full regression:

```text
python -m unittest discover -s tests -v
Ran 134 tests
OK
```

An offscreen launch of the real application with both flags enabled also
confirmed the runtime fail-safe. The currently installed local profile still
contains the legacy database layout and has no initialized Schema 1
`data/user.db`, so the expected output was:

```text
[AW0.2][SingleRow] attached
legacy_id=g-shooter-fps-002
contracts_id=9df7cc01-d487-4cd7-814d-e70ec7967a4a
[AW0.2][SingleRow] error
code=read_error
message=no such table: user_library_state
```

Velora remained running, the success marker was not shown, and no database was
created or changed by the read-only adapter.

Static checks:

```text
python -m compileall -q app velora_contracts tests
success

git diff --check
success
```

## Manual confirmation gate

The diagnostic code remains in place. Do not expand integration to additional
rows or connect write actions until the running application has been manually
checked and the marker/log output has been confirmed.
