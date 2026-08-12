"""Game-neutral Journey orchestration with a Doom legacy adapter."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from velora_contracts.enums import CheckpointType, SourceType
from velora_contracts.ids import OperationId
from velora_contracts.value_objects import CatalogItemRef
from app.storage.startup import DOOM_ETERNAL_ID
from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork
from .game_services import (
    GameProgressService, ImpressionService, JourneyService, PlaythroughService,
    RatingService,
)
from .game_row_contracts import GameRowAction, GameRowDto, QueryStateKind
from .game_row_queries import GamesRowQueryService
from .playthrough_history import GamePlaythroughHistoryQueryService
from .journey_templates import JourneyTemplateRegistry


@dataclass(frozen=True, slots=True)
class PlaythroughSummary:
    playthrough_id: str
    sequence_no: int
    status: str
    started_at: str | None
    ended_at: str | None
    playtime_minutes: int
    checkpoint: str | None
    final_rating_tenths: int | None
    last_activity_at: str | None = None
    is_current: bool = False


@dataclass(frozen=True, slots=True)
class ImpressionSummary:
    text: str
    checkpoint: str | None
    playthrough_sequence: int
    playtime_minutes: int | None
    created_at: str
    progress_value: float | None = None
    progress_unit: str | None = None


@dataclass(frozen=True, slots=True)
class RatingSummary:
    rating_type: str
    value_tenths: int | None
    checkpoint: str | None
    playthrough_sequence: int | None
    review_text: str | None
    is_current: bool
    created_at: str


@dataclass(frozen=True, slots=True)
class JourneySummary:
    title: str
    description: str
    playthrough_sequence: int | None
    occurred_at: str
    event_type: str = ""
    payload_json: str = "{}"
    playthrough_id: str | None = None
    event_id: str = ""


@dataclass(frozen=True, slots=True)
class GameJourneyDetailState:
    row: GameRowDto
    catalog_description: str | None
    actions: tuple[GameRowAction, ...]
    playthroughs: tuple[PlaythroughSummary, ...]
    impressions: tuple[ImpressionSummary, ...]
    ratings: tuple[RatingSummary, ...]
    journey: tuple[JourneySummary, ...]
    official_journey_template: dict | None = None
    stage_moods: tuple[tuple[str, str, str], ...] = ()
    stage_states: tuple[tuple[str, str, str], ...] = ()
    stage_ratings: tuple[tuple[str, str, int], ...] = ()
    stage_flags: tuple[tuple[str, str, bool, bool], ...] = ()


class GameJourneySlice:
    """Application boundary for one catalog game's official/personal Journey."""

    def __init__(
        self, catalog_db: Path, user_db: Path, ref: CatalogItemRef,
        *, legacy_template_id: str | None = None,
    ) -> None:
        self.catalog_db, self.user_db = Path(catalog_db), Path(user_db)
        self.ref = ref
        self._legacy_template_id = legacy_template_id
        self.playthroughs = PlaythroughService(self.user_db)
        self.progress = GameProgressService(self.user_db)
        self.impressions = ImpressionService(self.user_db)
        self.ratings = RatingService(self.user_db)
        self.journey = JourneyService(self.user_db)

    def set_status(self, status: str) -> None:
        target = {
            "НЕ НАЧИНАЛ": "planned",
            "ПРОХОЖУ": "playing",
            "ПРОШЁЛ": "completed",
            "ПРОШЕЛ": "completed",
            "БРОСИЛ": "abandoned",
        }.get(status.upper())
        if target is None:
            return
        current = self._current()
        if current is None:
            current = self.playthroughs.create(
                self.ref,
                OperationId.new(),
                initial_status="planned" if target == "planned" else "playing",
            )
            if target in {"planned", "playing"}:
                return
        elif target == "planned" and current.status in {"completed", "abandoned"}:
            self.playthroughs.create(
                self.ref, OperationId.new(), initial_status="planned",
            )
            return
        elif target == "playing" and current.status in {"completed", "abandoned"}:
            self.playthroughs.start(self.ref, OperationId.new())
            return
        if current.status != target:
            self.playthroughs.set_status(current.playthrough_id, target, OperationId.new())

    def create_playthrough(self) -> str:
        value = self.playthroughs.create_next(self.ref, OperationId.new())
        return value.playthrough_id

    def delete_playthrough(self, playthrough_id: str) -> str | None:
        result = self.playthroughs.delete(
            playthrough_id, OperationId.new()
        )
        return result.selected_playthrough_id

    def set_total_playtime_hours(
        self, total_hours: float, *, playthrough_id: str | None = None,
    ) -> None:
        wanted = max(0, round(float(total_hours) * 60))
        current = self._resolve_playthrough(playthrough_id)
        difference = wanted - current.playtime_minutes
        if difference > 0:
            self.playthroughs.add_playtime(current.playthrough_id, difference, OperationId.new())

    def add_playtime(
        self, hours: int, minutes: int, *, playthrough_id: str | None = None,
    ) -> None:
        amount = max(0, int(hours)) * 60 + max(0, int(minutes))
        if amount <= 0:
            return
        current = self._resolve_playthrough(playthrough_id)
        self.playthroughs.add_playtime(
            current.playthrough_id, amount, OperationId.new()
        )

    def save_final_rating(self, criteria: dict[str, int]) -> None:
        if not criteria:
            return
        tenths = {code: max(0, min(100, int(value) * 10))
                  for code, value in criteria.items()}
        current = self._current()
        self.ratings.save_final(
            self.ref, round(sum(tenths.values()) / len(tenths)), tenths,
            OperationId.new(), playthrough_id=current.playthrough_id if current else None,
        )

    def save_personal_rating(
        self, value: float, review: str = "", *, playthrough_id: str | None = None,
    ) -> None:
        current = self._resolve_playthrough(playthrough_id)
        self.ratings.save_final(
            self.ref,
            max(0, min(100, round(float(value) * 10))),
            {},
            OperationId.new(),
            review_text=review.strip() or None,
            playthrough_id=current.playthrough_id if current else None,
        )

    def add_checkpoint(self, checkpoint: CheckpointType) -> None:
        current = self._current() or self.playthroughs.start(self.ref, OperationId.new())
        self.progress.create_checkpoint(current.playthrough_id, checkpoint, OperationId.new())

    def save_checkpoint(
        self, checkpoint: CheckpointType, *, title: str = "",
        description: str = "", rating: float | None = None,
        playthrough_id: str | None = None,
    ) -> None:
        current = self._resolve_playthrough(playthrough_id)
        self.progress.create_checkpoint(
            current.playthrough_id, checkpoint, OperationId.new()
        )
        review = "\n".join(
            part.strip() for part in (title, description) if part.strip()
        )
        if rating is not None or review:
            self.ratings.save_checkpoint(
                current.playthrough_id,
                checkpoint,
                OperationId.new(),
                value_tenths=None if rating is None else round(rating * 10),
                review_text=review or None,
            )

    def add_impression(
        self, text: str, checkpoint: CheckpointType | None = None,
        *, progress_value: float | None = None,
        progress_unit: str | None = None, playthrough_id: str | None = None,
    ) -> None:
        current = self._resolve_playthrough(playthrough_id)
        self.impressions.create(
            current.playthrough_id,
            text,
            OperationId.new(),
            checkpoint_type=checkpoint,
            progress_value=progress_value,
            progress_unit=progress_unit,
            playtime_minutes_at_entry=current.playtime_minutes,
        )

    def set_stage_mood(
        self, stage_id: str, mood_id: str | None, *,
        playthrough_id: str | None = None,
    ) -> None:
        allowed = {
            "excited", "happy", "positive", "neutral",
            "tired", "bored", "disappointed", "angry",
        }
        if mood_id is not None and mood_id not in allowed:
            raise ValueError(f"Unknown mood id: {mood_id}")
        current = self._resolve_playthrough(playthrough_id)
        self.journey.set_stage_mood(
            current.playthrough_id, stage_id, mood_id, OperationId.new()
        )

    def set_stage_media(
        self, stage_id: str, source_path: str, *,
        playthrough_id: str | None = None,
    ) -> str:
        """Copy personal stage media locally and record it in Journey history."""
        current = self._resolve_playthrough(playthrough_id)
        source = Path(source_path)
        if not source.is_file():
            raise ValueError("Файл изображения не найден")
        if source.suffix.casefold() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Поддерживаются PNG, JPG и WEBP")
        media_dir = self.user_db.parent / "media" / "journey"
        media_dir.mkdir(parents=True, exist_ok=True)
        safe_stage = "".join(
            char if char.isalnum() or char in "-_" else "_" for char in stage_id
        )
        target = media_dir / (
            f"{current.playthrough_id}_{safe_stage}{source.suffix.casefold()}"
        )
        shutil.copy2(source, target)
        self.journey.set_stage_media(
            current.playthrough_id, stage_id, str(target.resolve()), OperationId.new()
        )
        return str(target)

    def set_stage_state(
        self, stage_id: str, state: str, *, playthrough_id: str | None = None,
    ) -> None:
        """Persist personal chapter progress without changing the run status."""
        current = self._resolve_playthrough(playthrough_id)
        stage_ids = self._ordered_stage_ids()
        self.journey.set_stage_state(
            current.playthrough_id, stage_id, state, OperationId.new(),
            ordered_stage_ids=stage_ids,
        )

    def add_timeline_event(
        self, stage_id: str, event_type: str, *, title: str = "", body: str = "",
        tags: tuple[str, ...] = (), media_path: str | None = None,
        rating_after: float | None = None, occurred_at: str | None = None,
        mood_id: str | None = None,
        playthrough_id: str | None = None,
    ) -> str:
        playthrough = self._resolve_playthrough(playthrough_id)
        return self.journey.add_timeline_event(
            playthrough.playthrough_id, event_type, stage_id, OperationId.new(),
            title=title, body=body, tags=tags, media_path=media_path,
            rating_after=(None if rating_after is None else round(rating_after * 10)),
            mood_id=mood_id, occurred_at=occurred_at,
        )

    def revise_timeline_event(
        self, event_id: str, *, title: str, body: str,
        tags: tuple[str, ...] = (), rating_after: float | None = None,
        mood_id: str | None = None,
        occurred_at: str | None = None,
        playthrough_id: str | None = None,
    ) -> str:
        playthrough = self._resolve_playthrough(playthrough_id)
        return self.journey.revise_timeline_event(
            playthrough.playthrough_id, event_id, OperationId.new(),
            title=title, body=body, tags=tags,
            rating_after=(
                None if rating_after is None else round(rating_after * 10)
            ),
            mood_id=mood_id, event_occurred_at=occurred_at,
        )

    def delete_timeline_event(
        self, event_id: str, *, playthrough_id: str | None = None,
    ) -> str:
        playthrough = self._resolve_playthrough(playthrough_id)
        return self.journey.delete_timeline_event(
            playthrough.playthrough_id, event_id, OperationId.new()
        )

    def set_stage_favorite(
        self, stage_id: str, favorite: bool, *, playthrough_id: str | None = None,
    ) -> None:
        playthrough = self._resolve_playthrough(playthrough_id)
        self.journey.set_stage_favorite(
            playthrough.playthrough_id, stage_id, favorite, OperationId.new()
        )

    def set_stage_rating(
        self, stage_id: str, rating: float, *, playthrough_id: str | None = None,
    ) -> None:
        playthrough = self._resolve_playthrough(playthrough_id)
        self.journey.set_stage_rating(
            playthrough.playthrough_id, stage_id,
            max(10, min(100, round(float(rating) * 10))), OperationId.new(),
        )

    def set_stage_difficult(
        self, stage_id: str, difficult: bool, *, playthrough_id: str | None = None,
    ) -> None:
        playthrough = self._resolve_playthrough(playthrough_id)
        self.journey.set_stage_difficult(
            playthrough.playthrough_id, stage_id, difficult, OperationId.new()
        )

    def load_detail(self) -> GameJourneyDetailState:
        query = GamesRowQueryService(self.catalog_db, self.user_db)
        row_state = query.get_game_row(self.ref)
        if row_state.kind is not QueryStateKind.RESULT or row_state.row is None:
            message = row_state.error.message if row_state.error else "Игра не найдена"
            raise RuntimeError(message)
        with CatalogUnitOfWork(self.catalog_db) as catalog_uow:
            catalog_item = catalog_uow.catalog.get(self.ref.item_id)
            template_payload = catalog_uow.catalog.payload(
                self.ref.item_id, "journey_template"
            )
        with UserUnitOfWork(self.user_db) as uow:
            runs = tuple(uow.playthroughs.list_for_item(
                self.ref.source_type, self.ref.item_id
            ))
            events = tuple(uow.journey.list_for_item(
                self.ref.source_type, self.ref.item_id
            ))
            ratings = tuple(uow.ratings.history(
                self.ref.source_type, self.ref.item_id
            ))
            impressions = tuple(
                impression
                for run in runs
                for impression in uow.impressions.list_for_playthrough(
                    run.playthrough_id
                )
            )
            stage_moods = tuple(
                (run.playthrough_id, stage_id, mood_id)
                for run in runs
                for stage_id, mood_id in sorted(
                    uow.journey_moods.list_for_playthrough(
                        run.playthrough_id
                    ).items()
                )
            )
            stage_states = tuple(
                (run.playthrough_id, stage_id, stage_state)
                for run in runs
                for stage_id, stage_state in sorted(
                    uow.journey_stage_states.list_for_playthrough(
                        run.playthrough_id
                    ).items()
                )
            )
            stage_ratings = tuple(
                (run.playthrough_id, stage_id, value_tenths)
                for run in runs
                for stage_id, value_tenths in sorted(
                    uow.journey_stage_ratings.list_for_playthrough(
                        run.playthrough_id
                    ).items()
                )
            )
            stage_flags = tuple(
                (run.playthrough_id, stage_id, values[0], values[1])
                for run in runs
                for stage_id, values in sorted(
                    uow.journey_stage_flags.list_for_playthrough(
                        run.playthrough_id
                    ).items()
                )
            )
        run_by_id = {run.playthrough_id: run for run in runs}
        latest_checkpoints: dict[str, str] = {}
        for event in events:
            if event.event_type == "milestone_recorded" and event.playthrough_id:
                latest_checkpoints[event.playthrough_id] = str(
                    json.loads(event.payload_json).get("checkpoint_type") or ""
                )
        final_by_run = {
            rating.playthrough_id: rating.value_tenths
            for rating in ratings
            if rating.rating_type.value == "final" and rating.playthrough_id
        }
        history = GamePlaythroughHistoryQueryService(self.user_db).get(self.ref)
        history_by_id = {
            item.playthrough.playthrough_id: item for item in history.playthroughs
        }
        playthrough_summaries = tuple(
            PlaythroughSummary(
                run.playthrough_id, run.sequence_no, run.status,
                run.started_at, run.ended_at, run.playtime_minutes,
                latest_checkpoints.get(run.playthrough_id),
                final_by_run.get(run.playthrough_id),
                history_by_id[run.playthrough_id].last_activity_at,
                run.is_current,
            )
            for run in runs
        )
        impression_summaries = tuple(
            ImpressionSummary(
                item.text, item.checkpoint_type,
                run_by_id[item.playthrough_id].sequence_no,
                item.playtime_minutes_at_entry, item.created_at,
                item.progress_value, item.progress_unit,
            )
            for item in impressions
        )
        rating_summaries = tuple(
            RatingSummary(
                item.rating_type.value, item.value_tenths,
                item.checkpoint_type,
                run_by_id[item.playthrough_id].sequence_no
                if item.playthrough_id in run_by_id else None,
                item.review_text, item.is_current, item.created_at,
            )
            for item in ratings
        )
        journey_summaries = tuple(
            _journey_summary(event, run_by_id) for event in events
        )
        return GameJourneyDetailState(
            row_state.row,
            (
                catalog_item.description or catalog_item.short_description
                if catalog_item is not None else None
            ),
            query.resolve_row_actions(row_state.row),
            playthrough_summaries,
            impression_summaries,
            rating_summaries,
            journey_summaries,
            (
                json.loads(template_payload[1])
                if template_payload is not None else None
            ),
            stage_moods,
            stage_states,
            stage_ratings,
            stage_flags,
        )

    def _current(self):
        with UserUnitOfWork(self.user_db) as uow:
            return uow.playthroughs.get_current(self.ref.source_type, self.ref.item_id)

    def _resolve_playthrough(self, playthrough_id: str | None):
        with UserUnitOfWork(self.user_db) as uow:
            value = (
                uow.playthroughs.get(playthrough_id)
                if playthrough_id else
                uow.playthroughs.get_current(self.ref.source_type, self.ref.item_id)
            )
        if value is None:
            return self.playthroughs.start(self.ref, OperationId.new())
        if (value.source_type, value.item_id) != (
            self.ref.source_type, self.ref.item_id
        ):
            raise ValueError("Playthrough does not belong to the selected game")
        return value

    def _official_template(self):
        with CatalogUnitOfWork(self.catalog_db) as uow:
            payload = uow.catalog.payload(self.ref.item_id, "journey_template")
        decoded = json.loads(payload[1]) if payload is not None else None
        template = JourneyTemplateRegistry().from_payload(decoded)
        if template is not None:
            return template
        if self._legacy_template_id == "doom_eternal_reference":
            return JourneyTemplateRegistry().doom_eternal()
        return JourneyTemplateRegistry().get("story_campaign")

    def _ordered_stage_ids(self) -> tuple[str, ...]:
        template = self._official_template()
        return template.stage_ids or tuple(
            f"stage-{index:02d}"
            for index in range(1, len(template.stage_titles) + 1)
        )


class DoomVerticalSlice(GameJourneySlice):
    """Backward-compatible adapter; Doom uses the generic game pipeline."""

    ref = CatalogItemRef(SourceType.OFFICIAL, DOOM_ETERNAL_ID)

    def __init__(self, catalog_db: Path, user_db: Path) -> None:
        super().__init__(
            catalog_db, user_db, self.ref,
            legacy_template_id="doom_eternal_reference",
        )


# Public compatibility name retained for existing UI/tests during AW0.23.
DoomDetailState = GameJourneyDetailState


_EVENT_TITLES = {
    "library_added": "Добавлено в библиотеку",
    "playthrough_started": "Начато прохождение",
    "status_changed": "Изменён статус",
    "playtime_added": "Добавлено игровое время",
    "milestone_recorded": "Создана контрольная точка",
    "impression_added": "Добавлено впечатление",
    "rating_changed": "Изменена личная оценка",
    "playthrough_completed": "Прохождение завершено",
    "playthrough_abandoned": "Прохождение остановлено",
}


def _journey_summary(event, run_by_id: dict[str, object]) -> JourneySummary:
    data = json.loads(event.payload_json)
    title = _EVENT_TITLES.get(event.event_type, "Обновлена игра")
    if event.event_type == "playtime_added":
        description = f"Добавлено {int(data.get('minutes_added', 0))} мин."
    elif event.event_type == "milestone_recorded":
        labels = {"start": "Начало", "middle": "Середина", "end": "Финал"}
        description = labels.get(str(data.get("checkpoint_type")), "Новый этап")
    elif event.event_type == "rating_changed":
        value = data.get("value_tenths")
        description = (
            f"Оценка {int(value) / 10:.1f}" if value is not None
            else "Сохранена промежуточная оценка"
        )
    elif "from" in data and "to" in data:
        labels = {
            "planned": "Не начинал",
            "playing": "Прохожу",
            "completed": "Прошёл",
            "abandoned": "Бросил",
        }
        description = (
            f"{labels.get(str(data['from']), str(data['from']))} → "
            f"{labels.get(str(data['to']), str(data['to']))}"
        )
    else:
        description = ""
    run = run_by_id.get(event.playthrough_id or "")
    return JourneySummary(
        title, description, getattr(run, "sequence_no", None), event.occurred_at,
        event.event_type, event.payload_json, event.playthrough_id, event.event_id,
    )
