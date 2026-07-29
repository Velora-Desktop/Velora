"""Database-specific Units of Work with explicit transaction ownership."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType

from .repositories import (
    CatalogRepository, ImpressionRepository, JourneyRepository,
    LibraryRepository, PlaythroughRepository, RatingRepository,
    SystemStateRepository, UserItemRepository, UserTagRepository,
)
from .sqlite_policy import CatalogDbSession, SQLitePolicy, UserDbSession


class CatalogUnitOfWork:
    def __init__(self, database: Path, policy: SQLitePolicy | None = None) -> None:
        self._session = (policy or SQLitePolicy()).catalog_session(database)

    def __enter__(self) -> "CatalogUnitOfWork":
        self._session.__enter__()
        self.catalog = CatalogRepository(self._session.db)
        self.system = SystemStateRepository(self._session.db)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return self._session.__exit__(exc_type, exc, tb)


class UserUnitOfWork:
    def __init__(self, database: Path, policy: SQLitePolicy | None = None) -> None:
        self._session = (policy or SQLitePolicy()).user_session(database)

    def __enter__(self) -> "UserUnitOfWork":
        self._session.__enter__()
        db = self._session.db
        self.user_items = UserItemRepository(db)
        self.library = LibraryRepository(db)
        self.playthroughs = PlaythroughRepository(db)
        self.journey = JourneyRepository(db)
        self.ratings = RatingRepository(db)
        self.impressions = ImpressionRepository(db)
        self.tags = UserTagRepository(db)
        self.system = SystemStateRepository(db)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return self._session.__exit__(exc_type, exc, tb)
