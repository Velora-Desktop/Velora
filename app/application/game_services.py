"""Minimal Games Core vertical slice over Schema 1 repositories."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from velora_contracts.canonical_json import canonical_json_text
from velora_contracts.enums import (
    CheckpointType, LibraryMembershipState, RatingType, SourceType,
)
from velora_contracts.errors import ConflictError, NotFoundError, ValidationError
from velora_contracts.events import DomainEvent, utc_now_text
from velora_contracts.ids import EventId, OperationId, PlaythroughId, RatingId
from velora_contracts.value_objects import CatalogItemRef

from app.storage.models import (
    Impression, JourneyEvent, LibraryState, Playthrough, Rating,
)
from app.storage.schema import utc_now
from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork

from .events import InProcessEventDispatcher
from .game_read_models import GameRowReadModel


def _op(value: OperationId | str) -> OperationId:
    return value if isinstance(value, OperationId) else OperationId(str(value))


def _time(value: str | None) -> str:
    return value or utc_now_text()


class _Service:
    def __init__(
        self, user_db: Path, *,
        dispatcher: InProcessEventDispatcher | None = None,
    ) -> None:
        self.user_db = Path(user_db)
        self.dispatcher = dispatcher or InProcessEventDispatcher()

    def _journey(
        self, *, operation_id: OperationId, ref: CatalogItemRef,
        event_type: str, occurred_at: str, playthrough_id: str | None,
        data: dict[str, object],
    ) -> tuple[JourneyEvent, EventId]:
        event_id = EventId.new()
        return (
            JourneyEvent(
                str(event_id), str(operation_id), ref.source_type, ref.item_id,
                playthrough_id, event_type, 1, canonical_json_text(data), occurred_at,
            ),
            event_id,
        )

    def _notification(
        self, name: str, event_id: EventId, operation_id: OperationId,
        occurred_at: str, ref: CatalogItemRef, *,
        playthrough_id: str | None = None,
        changed_fields: tuple[str, ...] = (),
        data: dict[str, object] | None = None,
    ) -> DomainEvent:
        return DomainEvent(
            name, event_id, operation_id, occurred_at, ref, playthrough_id,
            changed_fields, data or {},
        )


class LibraryService(_Service):
    def __init__(
        self, catalog_db: Path, user_db: Path, *,
        dispatcher: InProcessEventDispatcher | None = None,
    ) -> None:
        super().__init__(user_db, dispatcher=dispatcher)
        self.catalog_db = Path(catalog_db)

    def add(
        self, ref: CatalogItemRef, operation_id: OperationId | str,
        *, occurred_at: str | None = None,
    ) -> LibraryState:
        operation = _op(operation_id)
        at = _time(occurred_at)
        self._verify_ref(ref)
        notification: DomainEvent | None = None
        with UserUnitOfWork(self.user_db) as uow:
            prior_event = uow.journey.get_by_operation(str(operation))
            existing = uow.library.get(ref.source_type, ref.item_id)
            if prior_event is not None or existing is not None:
                if existing is None:
                    raise ConflictError("Operation exists without library projection")
                return existing
            state = LibraryState(
                ref.source_type, ref.item_id, LibraryMembershipState.ACTIVE,
                False, None, None, None, 0, None, None, None, at,
            )
            uow.library.upsert(state)
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type="library_added",
                occurred_at=at, playthrough_id=None, data={"membership_state": "active"},
            )
            uow.journey.append(journey)
            notification = self._notification(
                "LibraryItemAdded.v1", event_id, operation, at, ref,
                changed_fields=("membership_state",),
                data={"membership_state": "active"},
            )
        self.dispatcher.publish(notification)
        return state

    def _verify_ref(self, ref: CatalogItemRef) -> None:
        if ref.source_type is SourceType.OFFICIAL:
            with CatalogUnitOfWork(self.catalog_db) as uow:
                if uow.catalog.get(ref.item_id) is None:
                    raise NotFoundError("Official catalog item was not found")
        else:
            with UserUnitOfWork(self.user_db) as uow:
                if uow.user_items.get(ref.item_id) is None:
                    raise NotFoundError("User item was not found")


class PlaythroughService(_Service):
    _TRANSITIONS = {
        "planned": {"playing", "abandoned"},
        "playing": {"planned", "completed", "abandoned"},
        "completed": set(),
        "abandoned": {"playing"},
    }

    def create(
        self, ref: CatalogItemRef, operation_id: OperationId | str, *,
        initial_status: str = "planned", started_at: str | None = None,
    ) -> Playthrough:
        if initial_status not in {"planned", "playing"}:
            raise ValidationError("Initial playthrough status must be planned or playing")
        operation, at = _op(operation_id), _time(started_at)
        notification = None
        with UserUnitOfWork(self.user_db) as uow:
            previous = uow.journey.get_by_operation(str(operation))
            if previous:
                value = uow.playthroughs.get(previous.playthrough_id or "")
                if value is None:
                    raise ConflictError("Idempotent playthrough result is missing")
                return value
            library = uow.library.get(ref.source_type, ref.item_id)
            if library is None:
                raise NotFoundError("Game is not in the library")
            current = uow.playthroughs.get_current(ref.source_type, ref.item_id)
            if current is not None:
                if current.status in {"completed", "abandoned"}:
                    uow.playthroughs.retire_current(ref.source_type, ref.item_id)
                else:
                    raise ConflictError("A current playthrough already exists")
            value = Playthrough(
                str(PlaythroughId.new()), ref.source_type, ref.item_id,
                uow.playthroughs.next_sequence(ref.source_type, ref.item_id),
                initial_status, at if initial_status == "playing" else None,
                None, 0, None, None, True, None,
            )
            uow.playthroughs.add(value)
            projected = _project(library, value, at)
            uow.library.upsert(projected)
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type="playthrough_started",
                occurred_at=at, playthrough_id=value.playthrough_id,
                data={"status": initial_status, "sequence_no": value.sequence_no},
            )
            uow.journey.append(journey)
            notification = self._notification(
                "PlaythroughStarted.v1", event_id, operation, at, ref,
                playthrough_id=value.playthrough_id,
                changed_fields=("projected_status", "current_playthrough"),
                data={"status": initial_status},
            )
        self.dispatcher.publish(notification)
        return value

    def start(
        self, ref: CatalogItemRef, operation_id: OperationId | str,
        *, started_at: str | None = None,
    ) -> Playthrough:
        return self.create(
            ref, operation_id, initial_status="playing", started_at=started_at
        )

    def set_status(
        self, playthrough_id: str, status: str, operation_id: OperationId | str,
        *, occurred_at: str | None = None,
    ) -> Playthrough:
        operation, at = _op(operation_id), _time(occurred_at)
        notification = None
        with UserUnitOfWork(self.user_db) as uow:
            prior = uow.journey.get_by_operation(str(operation))
            value = uow.playthroughs.get(playthrough_id)
            if value is None:
                raise NotFoundError("Playthrough was not found")
            if prior:
                return value
            if status not in self._TRANSITIONS.get(value.status, set()):
                raise ConflictError(f"Illegal status transition: {value.status} -> {status}")
            started = value.started_at or (at if status == "playing" else None)
            ended = at if status in {"completed", "abandoned"} else None
            uow.playthroughs.update_state(
                playthrough_id, status=status, playtime_minutes=value.playtime_minutes,
                progress_value=value.progress_value, progress_unit=value.progress_unit,
                started_at=started, ended_at=ended,
            )
            updated = Playthrough(
                value.playthrough_id, value.source_type, value.item_id,
                value.sequence_no, status, started, ended, value.playtime_minutes,
                value.progress_value, value.progress_unit, value.is_current,
                value.deleted_at,
            )
            ref = CatalogItemRef(value.source_type, value.item_id)
            library = uow.library.get(value.source_type, value.item_id)
            if library is None:
                raise NotFoundError("Library projection was not found")
            uow.library.upsert(_project(library, updated, at))
            event_type = (
                "playthrough_completed" if status == "completed"
                else "playthrough_abandoned" if status == "abandoned"
                else "status_changed"
            )
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type=event_type,
                occurred_at=at, playthrough_id=playthrough_id,
                data={"from": value.status, "to": status},
            )
            uow.journey.append(journey)
            event_name = (
                "PlaythroughStatusChanged.v1"
            )
            notification = self._notification(
                event_name, event_id, operation, at, ref,
                playthrough_id=playthrough_id, changed_fields=("status",),
                data={"from": value.status, "to": status},
            )
        self.dispatcher.publish(notification)
        return updated

    def add_playtime(
        self, playthrough_id: str, minutes: int, operation_id: OperationId | str,
        *, occurred_at: str | None = None,
    ) -> Playthrough:
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
            raise ValidationError("Playtime must be a positive whole number of minutes")
        operation, at = _op(operation_id), _time(occurred_at)
        notification = None
        with UserUnitOfWork(self.user_db) as uow:
            prior = uow.journey.get_by_operation(str(operation))
            value = uow.playthroughs.get(playthrough_id)
            if value is None:
                raise NotFoundError("Playthrough was not found")
            if prior:
                return value
            total = value.playtime_minutes + minutes
            uow.playthroughs.update_state(
                playthrough_id, status=value.status, playtime_minutes=total,
                progress_value=value.progress_value, progress_unit=value.progress_unit,
                started_at=value.started_at, ended_at=value.ended_at,
            )
            updated = Playthrough(
                value.playthrough_id, value.source_type, value.item_id,
                value.sequence_no, value.status, value.started_at, value.ended_at,
                total, value.progress_value, value.progress_unit, value.is_current,
                value.deleted_at,
            )
            ref = CatalogItemRef(value.source_type, value.item_id)
            library = uow.library.get(value.source_type, value.item_id)
            if library is None:
                raise NotFoundError("Library projection was not found")
            all_runs = uow.playthroughs.list_for_item(value.source_type, value.item_id)
            projected_total = sum(
                total if run.playthrough_id == playthrough_id else run.playtime_minutes
                for run in all_runs if run.deleted_at is None
            )
            projected = _project(library, updated, at, total_playtime=projected_total)
            uow.library.upsert(projected)
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type="playtime_added",
                occurred_at=at, playthrough_id=playthrough_id,
                data={"minutes_added": minutes, "playthrough_total_minutes": total},
            )
            uow.journey.append(journey)
            notification = self._notification(
                "PlaytimeAdded.v1", event_id, operation, at, ref,
                playthrough_id=playthrough_id,
                changed_fields=("playtime_minutes", "projected_total_playtime_minutes"),
                data={"minutes_added": minutes, "total_minutes": total},
            )
        self.dispatcher.publish(notification)
        return updated


class GameProgressService(_Service):
    def create_checkpoint(
        self, playthrough_id: str, checkpoint_type: CheckpointType | str,
        operation_id: OperationId | str, *, occurred_at: str | None = None,
    ) -> str:
        checkpoint = CheckpointType(checkpoint_type)
        operation, at = _op(operation_id), _time(occurred_at)
        with UserUnitOfWork(self.user_db) as uow:
            prior = uow.journey.get_by_operation(str(operation))
            if prior:
                return str(json.loads(prior.payload_json)["checkpoint_type"])
            value = uow.playthroughs.get(playthrough_id)
            if value is None:
                raise NotFoundError("Playthrough was not found")
            ref = CatalogItemRef(value.source_type, value.item_id)
            journey, _ = self._journey(
                operation_id=operation, ref=ref, event_type="milestone_recorded",
                occurred_at=at, playthrough_id=playthrough_id,
                data={"checkpoint_type": checkpoint.value},
            )
            uow.journey.append(journey)
        return checkpoint.value


class ImpressionService(_Service):
    def create(
        self, playthrough_id: str, text: str, operation_id: OperationId | str, *,
        checkpoint_type: CheckpointType | str | None = None,
        progress_value: float | None = None, progress_unit: str | None = None,
        playtime_minutes_at_entry: int | None = None,
        occurred_at: str | None = None,
    ) -> Impression:
        if not text.strip():
            raise ValidationError("Impression text is required")
        checkpoint = CheckpointType(checkpoint_type).value if checkpoint_type else None
        operation, at = _op(operation_id), _time(occurred_at)
        notification = None
        with UserUnitOfWork(self.user_db) as uow:
            prior = uow.journey.get_by_operation(str(operation))
            value = uow.playthroughs.get(playthrough_id)
            if value is None:
                raise NotFoundError("Playthrough was not found")
            if prior:
                impression_id = json.loads(prior.payload_json)["impression_id"]
                result = uow.impressions.get(impression_id)
                if result is None:
                    raise ConflictError("Idempotent impression result is missing")
                return result
            result = Impression(
                str(uuid4()), playthrough_id, checkpoint, text.strip(),
                progress_value, progress_unit, playtime_minutes_at_entry, at,
            )
            uow.impressions.add(result)
            ref = CatalogItemRef(value.source_type, value.item_id)
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type="impression_added",
                occurred_at=at, playthrough_id=playthrough_id,
                data={"impression_id": result.impression_id,
                      "checkpoint_type": checkpoint},
            )
            uow.journey.append(journey)
            notification = self._notification(
                "ImpressionAdded.v1", event_id, operation, at, ref,
                playthrough_id=playthrough_id, changed_fields=("impression",),
                data={"impression_id": result.impression_id},
            )
        self.dispatcher.publish(notification)
        return result


class RatingService(_Service):
    def save_checkpoint(
        self, playthrough_id: str, checkpoint_type: CheckpointType | str,
        operation_id: OperationId | str, *, value_tenths: int | None = None,
        review_text: str | None = None, occurred_at: str | None = None,
    ) -> Rating:
        checkpoint = CheckpointType(checkpoint_type).value
        if value_tenths is not None and not 0 <= value_tenths <= 100:
            raise ValidationError("Rating must be between 0 and 100 tenths")
        if value_tenths is None and not (review_text or "").strip():
            raise ValidationError("Text-only checkpoint requires review text")
        operation, at = _op(operation_id), _time(occurred_at)
        notification = None
        with UserUnitOfWork(self.user_db) as uow:
            prior = uow.journey.get_by_operation(str(operation))
            playthrough = uow.playthroughs.get(playthrough_id)
            if playthrough is None:
                raise NotFoundError("Playthrough was not found")
            if prior:
                result = uow.ratings.get(json.loads(prior.payload_json)["rating_id"])
                if result is None:
                    raise ConflictError("Idempotent checkpoint rating is missing")
                return result
            uow.ratings.supersede_current_checkpoint(playthrough_id, checkpoint, at)
            result = Rating(
                str(RatingId.new()), playthrough.source_type, playthrough.item_id,
                playthrough_id, RatingType.CHECKPOINT, checkpoint, value_tenths,
                review_text, True, None, at, at,
            )
            uow.ratings.add(result)
            ref = CatalogItemRef(playthrough.source_type, playthrough.item_id)
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type="rating_changed",
                occurred_at=at, playthrough_id=playthrough_id,
                data={"rating_id": result.rating_id, "rating_type": "checkpoint",
                      "checkpoint_type": checkpoint},
            )
            uow.journey.append(journey)
            notification = self._notification(
                "CheckpointSaved.v1", event_id, operation, at, ref,
                playthrough_id=playthrough_id, changed_fields=("checkpoint_rating",),
                data={"rating_id": result.rating_id, "checkpoint_type": checkpoint},
            )
        self.dispatcher.publish(notification)
        return result

    def save_final(
        self, ref: CatalogItemRef, value_tenths: int,
        criteria: dict[str, int], operation_id: OperationId | str, *,
        review_text: str | None = None, playthrough_id: str | None = None,
        occurred_at: str | None = None,
    ) -> Rating:
        if not 0 <= value_tenths <= 100:
            raise ValidationError("Final rating must be between 0 and 100 tenths")
        if any(not 0 <= value <= 100 for value in criteria.values()):
            raise ValidationError("Criterion rating must be between 0 and 100 tenths")
        operation, at = _op(operation_id), _time(occurred_at)
        notification = None
        with UserUnitOfWork(self.user_db) as uow:
            prior = uow.journey.get_by_operation(str(operation))
            if prior:
                result = uow.ratings.get(json.loads(prior.payload_json)["rating_id"])
                if result is None:
                    raise ConflictError("Idempotent final rating is missing")
                return result
            if uow.library.get(ref.source_type, ref.item_id) is None:
                raise NotFoundError("Game is not in the library")
            if playthrough_id:
                playthrough = uow.playthroughs.get(playthrough_id)
                if playthrough is None or (
                    playthrough.source_type, playthrough.item_id
                ) != (ref.source_type, ref.item_id):
                    raise ValidationError("Playthrough does not belong to the rated game")
            uow.ratings.supersede_current_final(ref.source_type, ref.item_id, at)
            result = Rating(
                str(RatingId.new()), ref.source_type, ref.item_id, playthrough_id,
                RatingType.FINAL, None, value_tenths, review_text, True, None, at, at,
            )
            uow.ratings.add(result)
            for code, value in sorted(criteria.items()):
                uow.ratings.add_criterion(str(uuid4()), result.rating_id, code, value)
            journey, event_id = self._journey(
                operation_id=operation, ref=ref, event_type="rating_changed",
                occurred_at=at, playthrough_id=playthrough_id,
                data={"rating_id": result.rating_id, "rating_type": "final",
                      "value_tenths": value_tenths},
            )
            uow.journey.append(journey)
            notification = self._notification(
                "FinalRatingSaved.v1", event_id, operation, at, ref,
                playthrough_id=playthrough_id, changed_fields=("final_rating",),
                data={"rating_id": result.rating_id, "value_tenths": value_tenths},
            )
        self.dispatcher.publish(notification)
        return result


class JourneyService(_Service):
    def list_for_game(self, ref: CatalogItemRef) -> tuple[JourneyEvent, ...]:
        with UserUnitOfWork(self.user_db, ) as uow:
            return tuple(uow.journey.list_for_item(ref.source_type, ref.item_id))

    def get_game_row(
        self, catalog_db: Path, ref: CatalogItemRef,
    ) -> GameRowReadModel:
        with UserUnitOfWork(self.user_db) as uow:
            library = uow.library.get(ref.source_type, ref.item_id)
            if library is None:
                raise NotFoundError("Game is not in the library")
            playthrough = uow.playthroughs.get_current(ref.source_type, ref.item_id)
            rating = uow.ratings.get_current_final(ref.source_type, ref.item_id)
            impression = (
                uow.impressions.latest_for_playthrough(playthrough.playthrough_id)
                if playthrough else None
            )
            checkpoint_event = uow.journey.latest_of_type(
                ref.source_type, ref.item_id, "milestone_recorded"
            )
            user_item = (
                uow.user_items.get(ref.item_id)
                if ref.source_type is SourceType.USER else None
            )
        if ref.source_type is SourceType.OFFICIAL:
            with CatalogUnitOfWork(Path(catalog_db)) as catalog_uow:
                catalog_item = catalog_uow.catalog.get(ref.item_id)
                if catalog_item is None:
                    raise NotFoundError("Official catalog item was not found")
                title = catalog_item.canonical_title
        else:
            if user_item is None:
                raise NotFoundError("User item was not found")
            title = user_item.title
        checkpoint = (
            json.loads(checkpoint_event.payload_json).get("checkpoint_type")
            if checkpoint_event else None
        )
        preview = impression.text[:160] if impression else None
        return GameRowReadModel(
            ref.item_id if ref.source_type is SourceType.USER else None,
            ref, title, library.membership_state,
            playthrough.playthrough_id if playthrough else None,
            playthrough.status if playthrough else None,
            library.projected_total_playtime_minutes, checkpoint,
            rating.value_tenths if rating else None, preview, library.updated_at,
        )


def _project(
    library: LibraryState, playthrough: Playthrough, updated_at: str,
    *, total_playtime: int | None = None,
) -> LibraryState:
    return LibraryState(
        library.source_type, library.item_id, library.membership_state,
        library.favorite, playthrough.status, playthrough.progress_value,
        playthrough.progress_unit,
        playthrough.playtime_minutes if total_playtime is None else total_playtime,
        playthrough.started_at or library.started_at,
        playthrough.ended_at if playthrough.status == "completed" else library.completed_at,
        library.archived_at, updated_at,
    )
