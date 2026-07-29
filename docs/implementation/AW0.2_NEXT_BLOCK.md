# AW0.2 Next Block

Blocks 1 and 2 are complete. The narrow Block 3 Games Core Vertical Smoke
Slice is also complete and remains disconnected from the AW0.1 UI.

Block 4A Games Row Integration Preparation is complete. Its read-only facade,
typed filter/sort/page contracts and row DTO also remain disconnected from Qt.

Block 4B Single Games Row UI Integration is complete behind a disabled-by-
default feature flag. Only the existing Doom Eternal row has an opt-in
read-only adapter; no other row was migrated.

The next authorized work must be explicitly selected from the remaining
**Block 4 Core Services** scope:

1. Complete library lifecycle operations: archive and restore without deleting
   personal history.
2. Complete playthrough progress rules, resume/new-cycle behavior and
   projection rebuilding from authoritative playthroughs.
3. Add impression editing while preserving the required history.
4. Complete cross-reference link/unlink and unresolved official-reference
   projections.
5. Extend exact operation-id retry behavior across every remaining command.
6. Add the remaining core recovery and projection-rebuild smoke scenarios.

Required exit tests include:

- archive never deletes history;
- link/unlink preserves user identity;
- projected time equals the sum of non-deleted playthroughs;
- retry with the same `operation_id` returns the original command result;
- every projection mutation and Journey event share one `user.db` transaction;
- post-commit handler failures cannot roll back or corrupt committed state.

Remaining Implementation Plan stages:

- Block 5: search, images and catalog relations;
- Block 6: first Games UI render in VS Code;
- Block 7: Games analytics and output;
- Block 8: Studio 0.1;
- Block 9: patch and portable backup completion;
- Block 10: AW0.2 quality gate.

Do not migrate the remaining Games rows or connect write actions without a
separately authorized narrow block.
