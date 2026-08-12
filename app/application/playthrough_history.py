"""Read-only history of every playthrough for one catalog item.

The contract is UI-neutral and is intended to be shared by Journey, Creator,
and future analytics.  It never mutates storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from velora_contracts.value_objects import CatalogItemRef

from app.storage.models import (
    Impression,
    JourneyEvent,
    JourneyStageFlags,
    JourneyStageMood,
    JourneyStageRating,
    JourneyStageState,
    Playthrough,
    Rating,
)
from app.storage.unit_of_work import UserUnitOfWork


@dataclass(frozen=True, slots=True)
class PlaythroughHistoryEntry:
    playthrough: Playthrough
    created_at: str | None
    last_activity_at: str | None
    ratings: tuple[Rating, ...]
    stage_ratings: tuple[Rating, ...]
    moods: tuple[JourneyStageMood, ...]
    stage_states: tuple[JourneyStageState, ...]
    events: tuple[JourneyEvent, ...]
    notes: tuple[Impression, ...]
    normalized_stage_ratings: tuple[JourneyStageRating, ...] = ()
    stage_flags: tuple[JourneyStageFlags, ...] = ()
    visible_events: tuple[JourneyEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class GamePlaythroughHistoryReadModel:
    catalog_item_ref: CatalogItemRef
    playthroughs: tuple[PlaythroughHistoryEntry, ...]
    playthrough_count: int
    first_playthrough: PlaythroughHistoryEntry | None
    last_playthrough: PlaythroughHistoryEntry | None
    last_active_playthrough: PlaythroughHistoryEntry | None
    completed_playthroughs: tuple[PlaythroughHistoryEntry, ...]
    abandoned_playthroughs: tuple[PlaythroughHistoryEntry, ...]
    total_time_all_playthroughs_minutes: int
    ratings: tuple[Rating, ...]
    stage_ratings: tuple[Rating, ...]
    moods: tuple[JourneyStageMood, ...]
    events: tuple[JourneyEvent, ...]
    notes: tuple[Impression, ...]
    rating_changed_at: tuple[str, ...]
    visible_events: tuple[JourneyEvent, ...] = ()


VISIBLE_TIMELINE_EVENT_TYPES = frozenset({
    "note", "screenshot", "achievement", "favorite_moment",
    "difficult_moment", "music", "rating_change", "impression", "other",
})


class GamePlaythroughHistoryQueryService:
    """Build a deterministic aggregate from primary user.db records."""

    def __init__(self, user_db: Path) -> None:
        self.user_db = Path(user_db)

    def get(self, ref: CatalogItemRef) -> GamePlaythroughHistoryReadModel:
        with UserUnitOfWork(self.user_db) as uow:
            runs = tuple(uow.playthroughs.list_for_item(ref.source_type, ref.item_id))
            all_events = tuple(uow.journey.list_for_item(ref.source_type, ref.item_id))
            all_ratings = tuple(uow.ratings.history(ref.source_type, ref.item_id))
            entries: list[PlaythroughHistoryEntry] = []
            for run in runs:
                events = tuple(
                    item for item in all_events
                    if item.playthrough_id == run.playthrough_id
                )
                ratings = tuple(
                    item for item in all_ratings
                    if item.playthrough_id == run.playthrough_id
                )
                notes = tuple(uow.impressions.list_for_playthrough(run.playthrough_id))
                moods = tuple(
                    uow.journey_moods.list_records_for_playthrough(run.playthrough_id)
                )
                states = tuple(
                    uow.journey_stage_states.list_records_for_playthrough(
                        run.playthrough_id
                    )
                )
                normalized_ratings = tuple(
                    uow.journey_stage_ratings.list_records_for_playthrough(
                        run.playthrough_id
                    )
                )
                flags = tuple(
                    uow.journey_stage_flags.list_records_for_playthrough(
                        run.playthrough_id
                    )
                )
                visible_events = tuple(
                    item for item in events
                    if item.event_type in VISIBLE_TIMELINE_EVENT_TYPES
                )
                timestamps = [
                    value for value in (run.started_at, run.ended_at) if value
                ]
                timestamps.extend(item.occurred_at for item in events)
                timestamps.extend(item.updated_at for item in ratings)
                timestamps.extend(item.created_at for item in notes)
                timestamps.extend(item.updated_at for item in moods)
                timestamps.extend(item.updated_at for item in states)
                creation = next(
                    (
                        item.occurred_at for item in events
                        if item.event_type == "playthrough_started"
                    ),
                    run.started_at,
                )
                entries.append(PlaythroughHistoryEntry(
                    run,
                    creation,
                    max(timestamps) if timestamps else creation,
                    ratings,
                    tuple(item for item in ratings if item.rating_type.value == "checkpoint"),
                    moods,
                    states,
                    events,
                    notes,
                    normalized_ratings,
                    flags,
                    visible_events,
                ))

        values = tuple(entries)
        last_active = max(
            values,
            key=lambda item: (item.last_activity_at or "", item.playthrough.sequence_no),
            default=None,
        )
        stage_ratings = tuple(
            item for item in all_ratings if item.rating_type.value == "checkpoint"
        )
        return GamePlaythroughHistoryReadModel(
            ref,
            values,
            len(values),
            values[0] if values else None,
            values[-1] if values else None,
            last_active,
            tuple(item for item in values if item.playthrough.status == "completed"),
            tuple(item for item in values if item.playthrough.status == "abandoned"),
            sum(item.playthrough.playtime_minutes for item in values),
            all_ratings,
            stage_ratings,
            tuple(item for entry in values for item in entry.moods),
            all_events,
            tuple(item for entry in values for item in entry.notes),
            tuple(item.updated_at for item in all_ratings),
            tuple(
                item for item in all_events
                if item.event_type in VISIBLE_TIMELINE_EVENT_TYPES
            ),
        )
