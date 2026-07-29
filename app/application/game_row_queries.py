"""Read-only facade preparing Games rows for a future ViewModel."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from velora_contracts.enums import MediaType, SourceType
from velora_contracts.errors import DomainError
from velora_contracts.value_objects import CatalogItemRef

from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork

from .game_read_models import GameRowReadModel
from .game_row_contracts import (
    GameRowAction, GameRowDto, GameRowFilter, GameRowsState, GameRowSort,
    GameRowSortField, GameRowState, PageInfo, PageRequest, QueryError,
    QueryStateKind, RowSelectionIdentity, SortDirection,
)
from .game_services import JourneyService


class GamesRowQueryService:
    """Synchronous read-side with no cache, writes or UI dependencies."""

    def __init__(self, catalog_db: Path, user_db: Path) -> None:
        self.catalog_db = Path(catalog_db)
        self.user_db = Path(user_db)
        self._journey = JourneyService(self.user_db)

    def list_game_rows(
        self, *,
        filters: GameRowFilter | None = None,
        sort: GameRowSort | None = None,
        pagination: PageRequest | None = None,
    ) -> GameRowsState:
        try:
            rows = self._load_all_games()
            rows = tuple(row for row in rows if _matches(row, filters or GameRowFilter()))
            rows = _stable_sort(rows, sort or GameRowSort())
            request = pagination or PageRequest()
            total = len(rows)
            pages = (total + request.page_size - 1) // request.page_size
            start = (request.page - 1) * request.page_size
            selected = rows[start:start + request.page_size]
            info = PageInfo(request.page, request.page_size, total, pages)
            return GameRowsState(
                QueryStateKind.RESULT if selected else QueryStateKind.EMPTY,
                tuple(_to_dto(row) for row in selected), info,
            )
        except Exception as exc:
            return GameRowsState(QueryStateKind.ERROR, error=_error(exc))

    def get_game_row(self, ref: CatalogItemRef) -> GameRowState:
        try:
            return GameRowState(
                QueryStateKind.RESULT,
                _to_dto(self._journey.get_game_row(self.catalog_db, ref)),
            )
        except Exception as exc:
            return GameRowState(QueryStateKind.ERROR, error=_error(exc))

    def refresh_game_row(self, ref: CatalogItemRef) -> GameRowState:
        return self.get_game_row(ref)

    def resolve_row_actions(
        self, row: GameRowDto | GameRowReadModel,
    ) -> tuple[GameRowAction, ...]:
        actions = [GameRowAction.OPEN]
        status = row.playthrough_status
        if status in (None, "planned", "completed", "abandoned"):
            actions.append(GameRowAction.START_PLAYTHROUGH)
        if status == "playing":
            actions.extend((
                GameRowAction.CONTINUE_PLAYTHROUGH,
                GameRowAction.ADD_PLAYTIME,
                GameRowAction.ADD_CHECKPOINT,
                GameRowAction.ADD_IMPRESSION,
                GameRowAction.RATE,
                GameRowAction.COMPLETE_PLAYTHROUGH,
            ))
        elif status in ("completed", "abandoned"):
            actions.extend((GameRowAction.ADD_IMPRESSION, GameRowAction.RATE))
        return tuple(actions)

    def get_row_state(self, ref: CatalogItemRef) -> GameRowState:
        return self.get_game_row(ref)

    def _load_all_games(self) -> tuple[GameRowReadModel, ...]:
        with UserUnitOfWork(self.user_db) as user_uow:
            library = tuple(user_uow.library.list_all())
            user_items = {
                item.item_id: user_uow.user_items.get(item.item_id)
                for item in library if item.source_type is SourceType.USER
            }
        with CatalogUnitOfWork(self.catalog_db) as catalog_uow:
            catalog_items = {
                item.catalog_id: item for item in catalog_uow.catalog.list_all()
                if item.media_type is MediaType.GAME
            }
        refs: list[CatalogItemRef] = []
        for item in library:
            if item.source_type is SourceType.OFFICIAL:
                if item.item_id in catalog_items:
                    refs.append(CatalogItemRef(item.source_type, item.item_id))
            else:
                user_item = user_items.get(item.item_id)
                if user_item is not None and user_item.media_type is MediaType.GAME:
                    refs.append(CatalogItemRef(item.source_type, item.item_id))
        return tuple(
            self._journey.get_game_row(self.catalog_db, ref) for ref in refs
        )


def _to_dto(row: GameRowReadModel) -> GameRowDto:
    return GameRowDto(
        RowSelectionIdentity.from_ref(row.catalog_item_ref),
        row.catalog_item_ref, row.user_item_id, row.title,
        row.library_lifecycle_state, row.current_playthrough_id,
        row.playthrough_status, row.total_playtime_minutes,
        row.current_checkpoint, row.current_personal_rating_tenths,
        row.latest_impression_preview, row.updated_at,
    )


def _matches(row: GameRowReadModel, filters: GameRowFilter) -> bool:
    if (
        filters.lifecycle_state is not None
        and row.library_lifecycle_state is not filters.lifecycle_state
    ):
        return False
    if (
        filters.playthrough_status is not None
        and row.playthrough_status != filters.playthrough_status
    ):
        return False
    if (
        filters.has_rating is not None
        and (row.current_personal_rating_tenths is not None) != filters.has_rating
    ):
        return False
    active = row.playthrough_status in ("planned", "playing")
    if (
        filters.has_active_playthrough is not None
        and active != filters.has_active_playthrough
    ):
        return False
    return True


def _stable_sort(
    rows: Iterable[GameRowReadModel], contract: GameRowSort,
) -> tuple[GameRowReadModel, ...]:
    def stable_id(row: GameRowReadModel) -> tuple[str, str]:
        return row.catalog_item_ref.source_type.value, row.catalog_item_ref.item_id

    ordered = sorted(rows, key=stable_id)
    missing = [row for row in ordered if _sort_value(row, contract.field) is None]
    present = [row for row in ordered if _sort_value(row, contract.field) is not None]
    present.sort(
        key=lambda row: _sort_value(row, contract.field),
        reverse=contract.direction is SortDirection.DESCENDING,
    )
    return tuple(present + missing)


def _sort_value(row: GameRowReadModel, field: GameRowSortField):
    if field is GameRowSortField.TITLE:
        return row.title.casefold()
    if field is GameRowSortField.PERSONAL_RATING:
        return row.current_personal_rating_tenths
    if field is GameRowSortField.TOTAL_PLAYTIME:
        return row.total_playtime_minutes
    return row.updated_at


def _error(exc: Exception) -> QueryError:
    if isinstance(exc, DomainError):
        return QueryError(exc.code, exc.message)
    if isinstance(exc, ValueError):
        return QueryError("validation_error", str(exc))
    return QueryError("read_error", str(exc))
