"""UI-independent storage safety foundation."""

from .recovery import AtomicJsonJournal
from .snapshots import SnapshotCreator, SnapshotInfo, SnapshotVerifier
from .sqlite_policy import SQLitePolicy, SQLiteSession

__all__ = [
    "AtomicJsonJournal",
    "SQLitePolicy",
    "SQLiteSession",
    "SnapshotCreator",
    "SnapshotInfo",
    "SnapshotVerifier",
]
from .migrations import DiscoveredMigration, discover_migrations
from .models import (
    CatalogItem, Impression, JourneyEvent, LibraryState, Playthrough, Rating,
    SchemaMetadata, UserItem,
)
from .repositories import (
    CatalogRepository, ImpressionRepository, JourneyRepository,
    LibraryRepository, PlaythroughRepository, RatingRepository,
    SystemStateRepository, UserItemRepository,
)
from .reset import AW02ResetManager, ResetHardStop, ResetResult
from .schema import SchemaManager
from .unit_of_work import CatalogUnitOfWork, UserUnitOfWork

__all__ = [
    "AW02ResetManager", "CatalogItem", "CatalogRepository", "CatalogUnitOfWork",
    "DiscoveredMigration", "Impression", "ImpressionRepository", "JourneyEvent",
    "JourneyRepository", "LibraryRepository", "LibraryState", "Playthrough",
    "PlaythroughRepository", "Rating", "RatingRepository", "ResetHardStop",
    "ResetResult", "SchemaManager", "SchemaMetadata", "SystemStateRepository",
    "UserItem", "UserItemRepository", "UserUnitOfWork", "discover_migrations",
]
