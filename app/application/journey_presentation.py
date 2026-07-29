"""Read-model projection from existing AW0.2 data to Journey and Creator."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .doom_vertical_slice import DoomDetailState
from .journey_templates import JourneyTemplate, JourneyTemplateRegistry


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


@dataclass(frozen=True, slots=True)
class JourneyStage:
    stage_id: str
    title: str
    entries: tuple[JourneyEntry, ...]


@dataclass(frozen=True, slots=True)
class JourneyPresentation:
    template: JourneyTemplate
    game_id: str
    game_title: str
    playthrough_id: str | None
    playthrough_sequence: int | None
    status: str | None
    total_playtime_minutes: int
    stages: tuple[JourneyStage, ...]
    impressions: tuple[JourneyEntry, ...]
    ratings: tuple[JourneyEntry, ...]
    key_moments: tuple[JourneyEntry, ...]

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

    def build(
        self,
        state: DoomDetailState,
        template: JourneyTemplate | None = None,
        *,
        playthrough_sequence: int | None = None,
    ) -> JourneyPresentation:
        template = template or JourneyTemplateRegistry().resolve(title=state.row.title)
        current = next(
            (
                item for item in state.playthroughs
                if item.sequence_no == playthrough_sequence
            ),
            state.playthroughs[-1] if state.playthroughs else None,
        )
        sequence = current.sequence_no if current else None
        stage_titles = template.stage_titles or tuple(self._stage_labels.values())
        stage_ids = tuple(
            f"stage-{index:02d}" for index in range(1, len(stage_titles) + 1)
        )
        events: list[JourneyEntry] = []
        for item in state.journey:
            if sequence is not None and item.playthrough_sequence not in (None, sequence):
                continue
            stage = self._stage_from_text(
                f"{item.title} {item.description}", stage_titles, stage_ids
            )
            events.append(JourneyEntry(
                _id("event", item.title, item.occurred_at, item.playthrough_sequence),
                "event", item.title, item.description, item.occurred_at, stage,
                item.playthrough_sequence,
            ))
        impressions = tuple(JourneyEntry(
            _id("impression", item.text, item.created_at, item.playthrough_sequence),
            "impression", "Личное впечатление", item.text, item.created_at,
            self._impression_stage(item, stage_ids),
            item.playthrough_sequence,
        ) for item in state.impressions if sequence is None or item.playthrough_sequence == sequence)
        ratings = tuple(JourneyEntry(
            _id("rating", item.rating_type, item.created_at, item.playthrough_sequence),
            "rating", "Итоговая оценка" if item.rating_type == "final" else "Оценка этапа",
            item.review_text or "", item.created_at,
            self._stage_from_text(
                item.review_text or "", stage_titles, stage_ids
            ) or self._checkpoint_stage(item.checkpoint, stage_ids),
            item.playthrough_sequence,
            None if item.value_tenths is None else item.value_tenths / 10,
        ) for item in state.ratings if sequence is None or item.playthrough_sequence in (None, sequence))
        combined = events + list(impressions) + list(ratings)
        stages = tuple(
            JourneyStage(
                stage_id,
                title,
                tuple(item for item in combined if item.stage_id == stage_id),
            )
            for stage_id, title in zip(stage_ids, stage_titles)
        )
        key_moments = tuple(item for item in events if item.kind == "event" and (
            item.stage_id == stage_ids[-1]
            or "оцен" in item.title.casefold()
            or "заверш" in item.title.casefold()
        ))
        return JourneyPresentation(
            template, state.row.catalog_item_ref.item_id, state.row.title,
            current.playthrough_id if current else None, sequence,
            current.status if current else state.row.playthrough_status,
            current.playtime_minutes if current else state.row.total_playtime_minutes,
            stages, impressions, ratings, key_moments,
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
