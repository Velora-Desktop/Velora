"""Read-model projection from existing AW0.2 data to Journey and Creator."""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json

from .doom_vertical_slice import GameJourneyDetailState
from .journey_templates import JourneyTemplate, JourneyTemplateRegistry
from app.storage.startup import DOOM_ETERNAL_ID


@dataclass(frozen=True, slots=True)
class JourneyEntry:
    source_id: str
    kind: str
    title: str
    body: str
    occurred_at: str
    stage_id: str | None
    playthrough_sequence: int | None
    rating: float | None = None
    tags: tuple[str, ...] = ()
    media_path: str | None = None
    rating_before: float | None = None
    rating_after: float | None = None
    mood_id: str | None = None


@dataclass(frozen=True, slots=True)
class JourneyStage:
    stage_id: str
    title: str
    entries: tuple[JourneyEntry, ...]
    mood_id: str | None = None
    state: str = "not_started"
    favorite: bool = False
    media_path: str | None = None
    rating: float | None = None
    difficult: bool = False


@dataclass(frozen=True, slots=True)
class JourneyPlaythroughOption:
    playthrough_id: str
    sequence_no: int
    status: str
    started_at: str | None
    last_activity_at: str | None
    is_current: bool


@dataclass(frozen=True, slots=True)
class JourneyPresentation:
    template: JourneyTemplate
    game_id: str
    game_title: str
    playthrough_id: str | None
    playthrough_sequence: int | None
    status: str | None
    total_playtime_minutes: int
    started_at: str | None
    ended_at: str | None
    playthroughs: tuple[tuple[int, str], ...]
    stages: tuple[JourneyStage, ...]
    impressions: tuple[JourneyEntry, ...]
    ratings: tuple[JourneyEntry, ...]
    key_moments: tuple[JourneyEntry, ...]
    playthrough_options: tuple[JourneyPlaythroughOption, ...] = ()
    last_activity_at: str | None = None

    @property
    def all_sources(self) -> tuple[JourneyEntry, ...]:
        values = [entry for stage in self.stages for entry in stage.entries]
        values.extend(self.impressions)
        values.extend(self.ratings)
        seen: set[str] = set()
        return tuple(item for item in values if not (item.source_id in seen or seen.add(item.source_id)))


def _id(kind: str, *parts: object) -> str:
    return f"{kind}:{sha256('|'.join(map(str, parts)).encode('utf-8')).hexdigest()[:20]}"


class JourneyPresentationBuilder:
    _stage_labels = {"start": "Начало пути", "middle": "Переломный момент", "end": "Финал"}
    VISIBLE_TIMELINE_EVENT_TYPES = frozenset({
        "note", "screenshot", "achievement", "favorite_moment",
        "difficult_moment", "music", "rating_change", "impression", "other",
    })
    EVENT_DEFAULT_TITLES = {
        "note": "Заметка", "screenshot": "Скриншот",
        "achievement": "Достижение", "favorite_moment": "Любимый момент",
        "difficult_moment": "Сложный момент", "music": "Музыка",
        "rating_change": "Изменение оценки", "impression": "Личное впечатление",
        "other": "Другое событие",
    }

    def build(
        self,
        state: GameJourneyDetailState,
        template: JourneyTemplate | None = None,
        *,
        playthrough_sequence: int | None = None,
        playthrough_id: str | None = None,
    ) -> JourneyPresentation:
        if template is None:
            template = JourneyTemplateRegistry().from_payload(
                state.official_journey_template
            )
        # Legacy records created before catalog Journey payloads existed keep
        # their reference structure at this data boundary only. UI remains
        # game-neutral and consumes the same JourneyPresentation contract.
        if template is None and state.row.catalog_item_ref.item_id == DOOM_ETERNAL_ID:
            template = JourneyTemplateRegistry().doom_eternal()
        template = template or JourneyTemplateRegistry().get("story_campaign")
        current = next(
            (
                item for item in state.playthroughs
                if (
                    item.playthrough_id == playthrough_id
                    if playthrough_id is not None
                    else item.sequence_no == playthrough_sequence
                )
            ),
            state.playthroughs[-1] if state.playthroughs else None,
        )
        sequence = current.sequence_no if current else None
        stage_titles = template.stage_titles or tuple(self._stage_labels.values())
        stage_ids = template.stage_ids or tuple(
            f"stage-{index:02d}" for index in range(1, len(stage_titles) + 1)
        )
        events: list[JourneyEntry] = []
        revisions: dict[str, dict] = {}
        deleted_event_ids: set[str] = set()
        for item in state.journey:
            if item.event_type not in {"timeline_event_revised", "timeline_event_deleted"}:
                continue
            try:
                revision = json.loads(item.payload_json)
            except (TypeError, ValueError):
                revision = {}
            target = str(revision.get("target_event_id") or "")
            if target and item.event_type == "timeline_event_deleted":
                deleted_event_ids.add(target)
            elif target:
                revisions[target] = revision

        def project_revision(entry: JourneyEntry) -> JourneyEntry | None:
            """Apply immutable edits to both typed and legacy Journey entries."""
            if entry.source_id in deleted_event_ids:
                return None
            revision = revisions.get(entry.source_id)
            if not revision:
                return entry
            raw_rating = revision.get("rating_after", entry.rating_after)
            rating = (
                None if raw_rating is None else int(raw_rating) / 10
            )
            return replace(
                entry,
                title=str(revision.get("title", entry.title)).strip()
                or entry.title,
                body=str(revision.get("body", entry.body)).strip(),
                occurred_at=str(
                    revision.get("occurred_at") or entry.occurred_at
                ),
                rating=rating,
                rating_after=rating,
                tags=tuple(
                    str(tag) for tag in revision.get("tags", entry.tags)
                    if str(tag).strip()
                ),
                mood_id=str(
                    revision.get("mood_id", entry.mood_id) or ""
                ).strip() or None,
            )
        favorites: dict[str, bool] = {}
        media_paths: dict[str, str] = {}
        for item in state.journey:
            if item.event_type in {"timeline_event_revised", "timeline_event_deleted"}:
                continue
            if item.event_type == "stage_favorite_set":
                if current is not None and item.playthrough_id == current.playthrough_id:
                    try:
                        payload = json.loads(item.payload_json)
                    except (TypeError, ValueError):
                        payload = {}
                    stage_id = str(payload.get("stage_id", ""))
                    if stage_id:
                        favorites[stage_id] = bool(payload.get("favorite"))
                continue
            if item.event_type == "stage_media_set":
                if current is not None and item.playthrough_id == current.playthrough_id:
                    try:
                        payload = json.loads(item.payload_json)
                    except (TypeError, ValueError):
                        payload = {}
                    stage_id = str(payload.get("stage_id", ""))
                    file_path = str(payload.get("file_path", ""))
                    if stage_id and file_path:
                        media_paths[stage_id] = file_path
                continue
            if item.event_type in self.VISIBLE_TIMELINE_EVENT_TYPES:
                if current is not None and item.playthrough_id != current.playthrough_id:
                    continue
                try:
                    payload = json.loads(item.payload_json)
                except (TypeError, ValueError):
                    payload = {}
                stage_id = str(payload.get("stage_id") or "").strip()
                if stage_id not in stage_ids:
                    # New visible records never guess their anchor from text.
                    continue
                before = payload.get("rating_before")
                event_id = item.event_id or _id("event", item.event_type, item.occurred_at)
                if event_id in deleted_event_ids:
                    continue
                revision = revisions.get(event_id, {})
                after = revision.get("rating_after", payload.get("rating_after"))
                event_occurred_at = str(
                    revision.get("occurred_at") or item.occurred_at
                )
                mood_id = str(
                    revision.get("mood_id", payload.get("mood_id")) or ""
                ).strip() or None
                stored_title = str(
                    revision.get("title", payload.get("title") or "")
                ).strip()
                events.append(JourneyEntry(
                    event_id,
                    item.event_type,
                    stored_title or self.EVENT_DEFAULT_TITLES.get(
                        item.event_type, "Событие"
                    ),
                    str(revision.get("body", payload.get("body") or item.description or "")),
                    event_occurred_at, stage_id, item.playthrough_sequence,
                    None if after is None else int(after) / 10,
                    tuple(str(tag) for tag in revision.get("tags", payload.get("tags", ())) if str(tag).strip()),
                    str(payload.get("media_path") or "") or None,
                    None if before is None else int(before) / 10,
                    None if after is None else int(after) / 10,
                    mood_id,
                ))
                continue
            # Storage-only activity markers keep last_activity_at reliable;
            # they are not additional visual Timeline events.
            if item.event_type or (item.title == "Обновлена игра" and not item.description):
                continue
            if sequence is not None and item.playthrough_sequence not in (None, sequence):
                continue
            stage = self._stage_from_text(
                f"{item.title} {item.description}", stage_titles, stage_ids
            )
            legacy_entry = project_revision(JourneyEntry(
                _id("event", item.title, item.occurred_at, item.playthrough_sequence),
                "legacy", item.title, item.description, item.occurred_at, stage,
                item.playthrough_sequence,
            ))
            if legacy_entry is not None:
                events.append(legacy_entry)
        impression_entries: list[JourneyEntry] = []
        for item in state.impressions:
            if sequence is not None and item.playthrough_sequence != sequence:
                continue
            entry = project_revision(JourneyEntry(
                _id("impression", item.text, item.created_at, item.playthrough_sequence),
                "impression", "Личное впечатление", item.text, item.created_at,
                self._impression_stage(item, stage_ids),
                item.playthrough_sequence,
                None,
                self._legacy_tags(item.text),
            ))
            if entry is not None:
                impression_entries.append(entry)
        impressions = tuple(impression_entries)
        rating_entries: list[JourneyEntry] = []
        for item in state.ratings:
            if sequence is not None and item.playthrough_sequence not in (None, sequence):
                continue
            entry = project_revision(JourneyEntry(
                _id("rating", item.rating_type, item.created_at, item.playthrough_sequence),
                "rating", "Итоговая оценка" if item.rating_type == "final" else "Оценка этапа",
                item.review_text or "", item.created_at,
                self._stage_from_text(
                    item.review_text or "", stage_titles, stage_ids
                ) or self._checkpoint_stage(item.checkpoint, stage_ids),
                item.playthrough_sequence,
                None if item.value_tenths is None else item.value_tenths / 10,
            ))
            if entry is not None:
                rating_entries.append(entry)
        ratings = tuple(rating_entries)
        combined = events + list(impressions) + list(ratings)
        moods = {
            stage_id: mood_id
            for stored_playthrough_id, stage_id, mood_id in state.stage_moods
            if current is not None and stored_playthrough_id == current.playthrough_id
        }
        stored_states = {
            stage_id: stage_state
            for playthrough_id, stage_id, stage_state in state.stage_states
            if current is not None and playthrough_id == current.playthrough_id
        }
        stored_ratings = {
            stage_id: value_tenths / 10
            for stored_playthrough_id, stage_id, value_tenths
            in state.stage_ratings
            if current is not None and stored_playthrough_id == current.playthrough_id
        }
        stored_flags = {
            stage_id: (favorite, difficult)
            for stored_playthrough_id, stage_id, favorite, difficult
            in state.stage_flags
            if current is not None and stored_playthrough_id == current.playthrough_id
        }
        if not stored_states and stage_ids:
            if current is not None and current.status == "completed":
                stored_states = {stage_id: "completed" for stage_id in stage_ids}
            elif current is not None and current.status == "abandoned":
                stored_states = {stage_ids[0]: "in_progress"}
            else:
                stored_states = {stage_ids[0]: "current"}
        stages = tuple(
            JourneyStage(
                stage_id,
                title,
                tuple(item for item in combined if item.stage_id == stage_id),
                moods.get(stage_id),
                stored_states.get(stage_id, "not_started"),
                stored_flags.get(stage_id, (favorites.get(stage_id, False), False))[0],
                media_paths.get(stage_id),
                stored_ratings.get(stage_id),
                stored_flags.get(stage_id, (False, False))[1],
            )
            for stage_id, title in zip(stage_ids, stage_titles)
        )
        key_moments = tuple(
            item for item in events
            if item.kind in {"favorite_moment", "achievement", "rating_change"}
        )
        return JourneyPresentation(
            template, state.row.catalog_item_ref.item_id, state.row.title,
            current.playthrough_id if current else None, sequence,
            current.status if current else state.row.playthrough_status,
            current.playtime_minutes if current else state.row.total_playtime_minutes,
            current.started_at if current else None,
            current.ended_at if current else None,
            tuple((item.sequence_no, item.status) for item in state.playthroughs),
            stages, impressions, ratings, key_moments,
            tuple(
                JourneyPlaythroughOption(
                    item.playthrough_id,
                    item.sequence_no,
                    item.status,
                    item.started_at,
                    item.last_activity_at,
                    item.is_current,
                )
                for item in state.playthroughs
            ),
            current.last_activity_at if current else None,
        )

    @staticmethod
    def _stage_from_text(
        text: str,
        stage_titles: tuple[str, ...],
        stage_ids: tuple[str, ...],
    ) -> str | None:
        value = text.casefold()
        for stage_id, title in zip(stage_ids, stage_titles):
            if title.casefold() in value:
                return stage_id
        if any(word in value for word in ("начал", "начато", "начало", "start")):
            return stage_ids[0]
        if any(word in value for word in ("финал", "заверш", "end")):
            return stage_ids[-1]
        if any(word in value for word in ("серед", "middle")):
            return stage_ids[len(stage_ids) // 2]
        return None

    @staticmethod
    def _checkpoint_stage(
        checkpoint: str | None, stage_ids: tuple[str, ...]
    ) -> str | None:
        return {
            "start": stage_ids[0],
            "middle": stage_ids[len(stage_ids) // 2],
            "end": stage_ids[-1],
        }.get(checkpoint or "")

    @staticmethod
    def _impression_stage(item, stage_ids: tuple[str, ...]) -> str | None:
        if (
            item.progress_unit == "journey_stage"
            and item.progress_value is not None
        ):
            index = max(0, min(len(stage_ids) - 1, int(item.progress_value) - 1))
            return stage_ids[index]
        return JourneyPresentationBuilder._checkpoint_stage(
            item.checkpoint, stage_ids
        )

    @staticmethod
    def _legacy_tags(text: str) -> tuple[str, ...]:
        """Read old inline hashtags without making them the new write contract."""
        return tuple(dict.fromkeys(
            token[1:].strip(".,;:!?()[]{}")
            for token in text.split()
            if token.startswith("#") and len(token) > 1
        ))
