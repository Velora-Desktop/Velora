"""Closed enums used by Contracts 1."""

from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    OFFICIAL = "official"
    USER = "user"


class MediaType(StrEnum):
    GAME = "game"
    FILM = "film"
    SERIES = "series"
    PROGRAM = "program"


class CatalogLifecycleState(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"
    WITHDRAWN = "withdrawn"


class LibraryMembershipState(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RatingType(StrEnum):
    CHECKPOINT = "checkpoint"
    FINAL = "final"


class CheckpointType(StrEnum):
    START = "start"
    MIDDLE = "middle"
    END = "end"


class RelationType(StrEnum):
    SEQUEL = "sequel"
    PREQUEL = "prequel"
    SPIN_OFF = "spin_off"
    REMAKE = "remake"
    REMASTER = "remaster"
    EXPANSION = "expansion"
    SAME_SERIES = "same_series"
    ALTERNATE_VERSION = "alternate_version"
    SPIRITUAL_SUCCESSOR = "spiritual_successor"


class SnapshotType(StrEnum):
    LEGACY_RESET = "legacy_reset"
    PRE_MIGRATION = "pre_migration"
    MANUAL = "manual"
    PRE_RESTORE = "pre_restore"


class UnresolvedReason(StrEnum):
    MISSING = "missing"
    WITHDRAWN = "withdrawn"
    INCOMPATIBLE_CATALOG = "incompatible_catalog"
