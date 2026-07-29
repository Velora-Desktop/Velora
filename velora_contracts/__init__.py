"""Shared, UI-independent contracts for Velora Core Generation 1."""

from .errors import (
    BackupError,
    CompatibilityError,
    ConflictError,
    DomainError,
    FatalStorageError,
    IntegrityError,
    MigrationError,
    NotFoundError,
    PatchError,
    RecoverableStorageError,
    ValidationError,
)
from .events import DomainEvent
from .ids import (
    AchievementId,
    CatalogId,
    EventId,
    OperationId,
    PlaythroughId,
    RatingId,
    SnapshotId,
    UserItemId,
)
from .value_objects import CatalogItemRef, UnresolvedOfficialRef

__all__ = [
    "AchievementId",
    "BackupError",
    "CatalogId",
    "CatalogItemRef",
    "CompatibilityError",
    "ConflictError",
    "DomainError",
    "DomainEvent",
    "EventId",
    "FatalStorageError",
    "IntegrityError",
    "MigrationError",
    "NotFoundError",
    "OperationId",
    "PatchError",
    "PlaythroughId",
    "RatingId",
    "RecoverableStorageError",
    "SnapshotId",
    "UnresolvedOfficialRef",
    "UserItemId",
    "ValidationError",
]
