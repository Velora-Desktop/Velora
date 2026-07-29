"""Read-only migration discovery for future product migrations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from velora_contracts.canonical_json import sha256_file
from velora_contracts.errors import ValidationError

_NAME = re.compile(r"^(?P<order>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")


@dataclass(frozen=True, slots=True)
class DiscoveredMigration:
    order: int
    migration_id: str
    path: Path
    checksum_sha256: str


def discover_migrations(directory: Path) -> tuple[DiscoveredMigration, ...]:
    root = Path(directory)
    if not root.exists():
        return ()
    values: list[DiscoveredMigration] = []
    for path in sorted(root.glob("*.sql")):
        match = _NAME.fullmatch(path.name)
        if match is None:
            raise ValidationError(f"Invalid migration filename: {path.name}")
        values.append(DiscoveredMigration(
            int(match["order"]), path.stem, path, sha256_file(path)
        ))
    if values:
        expected = list(range(values[0].order, values[0].order + len(values)))
        if [value.order for value in values] != expected:
            raise ValidationError("Migration sequence is not contiguous")
    return tuple(values)
