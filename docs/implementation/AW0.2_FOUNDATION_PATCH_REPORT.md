# AW0.2 Foundation Patch Report

Implementation status: **complete** for Block 1.

## Files added

### Contracts 1

- `velora_contracts/__init__.py` — stable public exports.
- `velora_contracts/ids.py` — opaque canonical lowercase UUID types.
- `velora_contracts/enums.py` — closed content-neutral enums.
- `velora_contracts/errors.py` — frozen domain error categories.
- `velora_contracts/value_objects.py` — `CatalogItemRef` and unresolved
  official reference.
- `velora_contracts/events.py` — closed AW0.2 post-commit notification
  payloads and round-trip serialization.
- `velora_contracts/canonical_json.py` — Canonical JSON Serializer v1 and
  SHA-256 helpers.
- `velora_contracts/validators.py` — Patch Format 1 manifest, checksum,
  media-manifest, operation and path validators.

### Safety storage foundation

- `app/storage/sqlite_policy.py` — foreign keys, busy timeout and explicit
  service-owned transaction context.
- `app/storage/recovery.py` — atomically persisted external JSON journals.
- `app/storage/snapshots.py` — SQLite Online Backup API snapshot creation,
  canonical manifest, media checksums and verification.
- `app/storage/__init__.py` — package exports.

### Tests

- `tests/test_aw02_contracts.py`
- `tests/test_aw02_patch_validation.py`
- `tests/test_aw02_storage_foundation.py`

### Implementation documentation

- `docs/implementation/AW0.2_SOURCE_AUDIT.md`
- `docs/implementation/AW0.2_FOUNDATION_PATCH_REPORT.md`
- `docs/implementation/AW0.2_NEXT_BLOCK.md`

## Files changed

- `app/core/paths.py` — converted to a backwards-compatible facade over
  content-neutral `AppPaths`; existing constants and resource resolution
  remain available to AW0.1 UI code.

## Old code reused

- The existing source-run project root and `%LOCALAPPDATA%\Velora` convention.
- Existing `app.core.paths` import surface.
- Python 3.12 standard-library SQLite, hashing and JSON facilities.
- Existing unittest discovery and AW0.1 regression suite.

## Old code quarantined

Nothing was deleted or moved. The experimental migration runner, Qt-bound
backup service, repositories and UI model remain operational for AW0.1 but
are not imported by the AW0.2 safety foundation.

## Contract mapping

- Core Design §§3, 12: typed IDs, references and shared errors.
- Public API Events v1.1: closed event names and common payload.
- Patch Operations v1.1 §§1–8: canonical JSON, hashes, safe package paths,
  manifests and operation envelopes.
- Patch/Migration/Reset/Backup Recovery v1.1: external atomic journal
  primitive.
- Backup Protocol v1.1: SQLite Online Backup copy, source schema/core
  metadata, parent operation ID, media checksums and verification.
- Core Design §13: one `AppPaths` component.
- Implementation Plan Block 1: explicit SQLite transaction ownership and
  no UI imports.
- Product Evolution Contract: all foundation modules remain independent of
  Games and future content modules.

## Verification

Commands:

```text
python -m unittest tests.test_aw02_contracts tests.test_aw02_patch_validation tests.test_aw02_storage_foundation -v
python -m compileall -q app velora_contracts tests
python -m unittest discover -s tests -v
```

Results:

- Block 1 tests: 14 passed.
- Full regression suite: 67 passed.
- Compile check: passed.
- Published Patch Hash Fixture v1: exact match.
- PySide/UI import boundary: passed.

## Deviations

None. No Games UI, Schema 1 creator, repository/service migration, reset
execution, migration engine, patch apply engine, Studio UI, executable or
installer was implemented.

## Deferred work

Blocks 2–10 remain as listed in `IMPLEMENTATION_PLAN_v3.0.md`. The immediate
next step is documented in `AW0.2_NEXT_BLOCK.md`.

## Exit decision

Block 1 exit criteria are satisfied. Block 2 may begin on explicit user
instruction.
