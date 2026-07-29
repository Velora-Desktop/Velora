"""Typed, UI-neutral contracts for Games library row queries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from velora_contracts.enums import LibraryMembershipState
from velora_contracts.value_objects import CatalogItemRef


class GameRowSortField(StrEnum):
    UPDATED_AT = "updated_at"
    TITLE = "title"
    PERSONAL_RATING = "personal_rating"
    TOTAL_PLAYTIME = "total_playtime"


class SortDirection(StrEnum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class GameRowAction(StrEnum):
    OPEN = "open"
    START_PLAYTHROUGH = "start_playthrough"
    CONTINUE_PLAYTHROUGH = "continue_playthrough"
    ADD_PLAYTIME = "add_playtime"
    ADD_CHECKPOINT = "add_checkpoint"
    ADD_IMPRESSION = "add_impression"
    RATE = "rate"
    COMPLETE_PLAYTHROUGH = "complete_playthrough"


class QueryStateKind(StrEnum):
    EMPTY = "empty"
    LOADING = "loading"
    ERROR = "error"
    RESULT = "result"


@dataclass(frozen=True, slots=True)
class GameRowFilter:
    lifecycle_state: LibraryMembershipState | None = None
    playthrough_status: str | None = None
    has_rating: bool | None = None
    has_active_playthrough: bool | None = None


@dataclass(frozen=True, slots=True)
class GameRowSort:
    field: GameRowSortField = GameRowSortField.UPDATED_AT
    direction: SortDirection = SortDirection.DESCENDING


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be at least 1")
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")


@dataclass(frozen=True, slots=True)
class PageInfo:
    page: int
    page_size: int
    total_items: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class RowSelectionIdentity:
    source_type: str
    item_id: str

    @classmethod
    def from_ref(cls, ref: CatalogItemRef) -> "RowSelectionIdentity":
        return cls(ref.source_type.value, ref.item_id)

    @property
    def stable_key(self) -> str:
        return f"{self.source_type}:{self.item_id}"


@dataclass(frozen=True, slots=True)
class GameRowDto:
    selection: RowSelectionIdentity
    catalog_item_ref: CatalogItemRef
    user_item_id: str | None
    title: str
    library_lifecycle_state: LibraryMembershipState
    current_playthrough_id: str | None
    playthrough_status: str | None
    total_playtime_minutes: int
    current_checkpoint: str | None
    current_personal_rating_tenths: int | None
    latest_impression_preview: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class QueryError:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class GameRowsState:
    kind: QueryStateKind
    rows: tuple[GameRowDto, ...] = ()
    page: PageInfo | None = None
    error: QueryError | None = None

    @classmethod
    def loading(cls) -> "GameRowsState":
        return cls(QueryStateKind.LOADING)


@dataclass(frozen=True, slots=True)
class GameRowState:
    kind: QueryStateKind
    row: GameRowDto | None = None
    error: QueryError | None = None

    @classmethod
    def loading(cls) -> "GameRowState":
        return cls(QueryStateKind.LOADING)

