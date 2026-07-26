from __future__ import annotations

import re


def split_entities(value: str) -> list[str]:
    """Split database entity lists without breaking names containing commas."""
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def compact_entities(value: str) -> tuple[str, str]:
    """Return a compact primary-name label and the complete tooltip text."""
    values = [part for part in split_entities(value) if not re.fullmatch(r"Q\d+", part)]
    if not values:
        return "—", "—"
    display = values[0] if len(values) == 1 else f"{values[0]}  +{len(values) - 1}"
    return display, "\n".join(values)
