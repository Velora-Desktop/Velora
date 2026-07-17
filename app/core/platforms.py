from __future__ import annotations

from collections.abc import Iterable


PLATFORM_ORDER = (
    ("windows", "pc"),
    ("playstation", "ps", "ps1", "ps2", "ps3", "ps4", "ps5", "psp", "psv", "ps vita"),
    ("xbox", "x360", "xone", "xsx", "series x", "series s"),
    ("nintendo", "switch", "switch2", "nes", "snes", "n64", "wii", "gamecube", "gc", "gb", "gba", "nds", "3ds"),
    ("linux",),
    ("macos", "mac", "apple"),
    ("android",),
    ("ios", "iphone", "ipad"),
    ("vr", "oculus", "quest"),
)


def platform_sort_key(value: str) -> tuple[int, str]:
    normalized = value.strip().casefold()
    for index, aliases in enumerate(PLATFORM_ORDER):
        if any(normalized == alias or normalized.startswith(f"{alias} ") for alias in aliases):
            return index, normalized
    return len(PLATFORM_ORDER), normalized


def sorted_platforms(values: Iterable[str]) -> list[str]:
    return sorted((value for value in values if value.strip()), key=platform_sort_key)


def split_platforms(value: str) -> list[str]:
    return sorted_platforms(part.strip() for part in value.replace(",", ";").split(";"))
