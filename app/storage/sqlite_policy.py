"""SQLite connection and explicit transaction ownership policy."""

from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

from velora_contracts.errors import RecoverableStorageError


@dataclass(frozen=True, slots=True)
class SQLitePolicy:
    busy_timeout_ms: int = 5000

    def connect(self, database: Path, *, read_only: bool = False) -> sqlite3.Connection:
        path = Path(database).expanduser().resolve()
        if not read_only:
            path.parent.mkdir(parents=True, exist_ok=True)
        target = f"file:{path.as_posix()}?mode=ro" if read_only else str(path)
        try:
            connection = sqlite3.connect(
                target,
                uri=read_only,
                isolation_level=None,
                timeout=self.busy_timeout_ms / 1000,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_ms)}")
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                connection.close()
                raise RecoverableStorageError("SQLite foreign keys could not be enabled")
            return connection
        except sqlite3.Error as exc:
            raise RecoverableStorageError(
                f"Could not open SQLite database: {path}", details={"path": str(path)}
            ) from exc

    def session(self, database: Path, *, immediate: bool = True) -> "SQLiteSession":
        return SQLiteSession(self, Path(database), immediate=immediate)

    def catalog_session(self, database: Path, *, immediate: bool = True) -> "CatalogDbSession":
        return CatalogDbSession(self, Path(database), immediate=immediate)

    def user_session(self, database: Path, *, immediate: bool = True) -> "UserDbSession":
        return UserDbSession(self, Path(database), immediate=immediate)


class SQLiteSession(AbstractContextManager[sqlite3.Connection]):
    """A service-owned transaction. Repositories receive its connection."""

    def __init__(self, policy: SQLitePolicy, database: Path, *, immediate: bool = True) -> None:
        self.policy = policy
        self.database = database
        self.immediate = immediate
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self.connection = self.policy.connect(self.database)
        self.connection.execute("BEGIN IMMEDIATE" if self.immediate else "BEGIN")
        return self.connection

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        assert self.connection is not None
        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()
            self.connection = None
        return False


class _TypedSQLiteSession(SQLiteSession):
    """Marker session that exposes a connection only inside its transaction."""

    def __enter__(self) -> "_TypedSQLiteSession":
        super().__enter__()
        return self

    @property
    def db(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("SQLite session is not active")
        return self.connection


class CatalogDbSession(_TypedSQLiteSession):
    pass


class UserDbSession(_TypedSQLiteSession):
    pass
