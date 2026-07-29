"""Default AW0.2 adapter for the approved Doom Eternal vertical slice."""

from __future__ import annotations

from dataclasses import dataclass

from app.application import (
    GameRowAction, GameRowState, GamesRowQueryService, QueryStateKind,
    RowSelectionIdentity,
)
from app.application.doom_vertical_slice import DoomVerticalSlice
from app.core.paths import AppPaths
from app.core.runtime import startup_storage
from app.storage.startup import DOOM_ETERNAL_ID
from velora_contracts.enums import SourceType
from velora_contracts.value_objects import CatalogItemRef


TARGET_LEGACY_GAME_ID = "g-shooter-fps-002"
TARGET_GAME_ID = DOOM_ETERNAL_ID

_STATUS_TEXT = {
    None: "НЕ НАЧИНАЛ",
    "planned": "НЕ НАЧИНАЛ",
    "playing": "ПРОХОЖУ",
    "completed": "ПРОШЁЛ",
    "abandoned": "БРОСИЛ",
}


@dataclass(frozen=True, slots=True)
class GameRowPresentation:
    kind: QueryStateKind
    selection: RowSelectionIdentity | None = None
    title: str | None = None
    lifecycle_state: str | None = None
    playthrough_status: str | None = None
    total_playtime_minutes: int | None = None
    checkpoint: str | None = None
    personal_rating: str = "—"
    impression_preview: str | None = None
    updated_at: str | None = None
    actions: tuple[GameRowAction, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    playthrough_sequence: int | None = None
    has_journey: bool = False


class SingleGameRowViewModel:
    def __init__(self, facade: GamesRowQueryService) -> None:
        self.facade = facade
        self.detail = DoomVerticalSlice(facade.catalog_db, facade.user_db)
        self.ref = CatalogItemRef(SourceType.OFFICIAL, TARGET_GAME_ID)
        self.selection = RowSelectionIdentity.from_ref(self.ref)

    def load(self) -> GameRowPresentation:
        return self._map(self.facade.get_row_state(self.ref))

    def refresh(self) -> GameRowPresentation:
        return self._map(self.facade.refresh_game_row(self.ref))

    def _map(self, state: GameRowState) -> GameRowPresentation:
        if state.kind is QueryStateKind.ERROR:
            return GameRowPresentation(
                state.kind, self.selection,
                error_code=state.error.code if state.error else "read_error",
                error_message=state.error.message if state.error else "Ошибка чтения",
            )
        if state.kind is not QueryStateKind.RESULT or state.row is None:
            return GameRowPresentation(state.kind, self.selection)
        row = state.row
        detail = self.detail.load_detail()
        current = detail.playthroughs[-1] if detail.playthroughs else None
        return GameRowPresentation(
            row and state.kind,
            row.selection,
            row.title,
            row.library_lifecycle_state.value,
            _STATUS_TEXT.get(row.playthrough_status, row.playthrough_status or "—"),
            row.total_playtime_minutes,
            row.current_checkpoint,
            f"{row.current_personal_rating_tenths / 10:.1f}"
            if row.current_personal_rating_tenths is not None else "—",
            row.latest_impression_preview,
            row.updated_at,
            self.facade.resolve_row_actions(row),
            playthrough_sequence=current.sequence_no if current else None,
            has_journey=bool(detail.journey),
        )


class SingleGameRowPresenter:
    """Updates only Doom Eternal and leaves the legacy row intact on failure."""

    target_catalog_id = TARGET_GAME_ID
    target_legacy_catalog_id = TARGET_LEGACY_GAME_ID

    def __init__(self, view_model: SingleGameRowViewModel) -> None:
        self.view_model = view_model

    def bind(self, row) -> GameRowPresentation:
        return self._apply(row, self.view_model.load())

    def refresh(self, row) -> GameRowPresentation:
        return self._apply(row, self.view_model.refresh())

    def _apply(self, row, value: GameRowPresentation) -> GameRowPresentation:
        row.aw02_state = value.kind
        row.aw02_selection_identity = value.selection
        row.aw02_available_actions = value.actions
        if value.kind is not QueryStateKind.RESULT:
            row.setToolTip(value.error_message or "")
            return value
        row.setToolTip("")
        row.game.title = value.title or row.game.title
        row.title_button.setText(value.title or row.title_button.text())
        # Keep the existing Quick View/detail input object synchronized with
        # the Schema 1 projection without letting those widgets read storage.
        row.game.status = value.playthrough_status or "НЕ НАЧИНАЛ"
        row.game.personal_score = value.personal_rating
        row.game.playtime_hours = (value.total_playtime_minutes or 0) / 60
        row.personal_score_label.setText(value.personal_rating)
        row.sync_interactive_surfaces()
        row.status_button.set_status(value.playthrough_status or "НЕ НАЧИНАЛ")
        row.status_button.setEnabled(True)
        row.personal_score_label.setEnabled(True)
        minutes = value.total_playtime_minutes or 0
        compact_time = f"{minutes // 60}ч{minutes % 60:02d}"
        checkpoint = {
            "start": "Начало", "middle": "Середина", "end": "Финал"
        }.get(value.checkpoint or "", "—")
        run = f"#{value.playthrough_sequence}" if value.playthrough_sequence else "без прохождения"
        journey = " · ● Journey" if value.has_journey else ""
        row.title_button.setText(
            f"{value.title or 'Doom Eternal'} · {run} · "
            f"{compact_time} · {checkpoint}{journey}"
        )
        # The catalog title stays a title. Playthrough number, playtime,
        # checkpoint and Journey remain available in the detail presentation.
        row.title_button.setText(value.title or "Doom Eternal")
        row.title_button.setToolTip(
            "Doom Eternal AW0.2: открыть Quick View; действия доступны в меню •••"
        )
        row.set_aw02_actions(value.actions)
        return value


def build_single_row_presenter(
    *, paths: AppPaths | None = None,
) -> SingleGameRowPresenter | None:
    try:
        storage = startup_storage()
        if storage is None:
            return None
        facade = GamesRowQueryService(storage.catalog_db, storage.user_db)
        return SingleGameRowPresenter(SingleGameRowViewModel(facade))
    except Exception as exc:
        print(
            f"[AW0.2][SingleRow] fallback={type(exc).__name__}: {exc}",
            flush=True,
        )
        return None
