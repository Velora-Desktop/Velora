"""Creator source projection. No Creator persistence or UI dependency."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .journey_presentation import JourneyEntry, JourneyPresentation


@dataclass(frozen=True, slots=True)
class CreatorSourceItem:
    source_id: str
    source_type: str
    title: str
    body: str
    created_at: str
    stage_id: str | None
    rating: float | None
    is_selected_for_creator: bool
    ordering: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreatorSourceModel:
    game_id: str
    game_title: str
    playthrough_id: str | None
    journey_template_id: str
    journey_title: str
    journey_type: str
    playthrough_status: str | None
    total_playtime_minutes: int
    sources: tuple[CreatorSourceItem, ...]

    @property
    def selected_sources(self) -> tuple[CreatorSourceItem, ...]:
        return tuple(item for item in self.sources if item.is_selected_for_creator)


class CreatorMarkSession:
    """Deprecated compatibility shim.

    AW0.21 exposes every relevant Journey material to Creator automatically.
    Existing callers can still query the class while older UI code is removed.
    """
    _selected: set[str] = set()

    @classmethod
    def toggle(cls, source_id: str) -> bool:
        if source_id in cls._selected:
            cls._selected.remove(source_id)
            return False
        cls._selected.add(source_id)
        return True

    @classmethod
    def selected(cls) -> frozenset[str]:
        return frozenset(cls._selected)


class CreatorSourceBuilder:
    def build(self, journey: JourneyPresentation) -> CreatorSourceModel:
        sources = tuple(self._map(entry, index)
                        for index, entry in enumerate(journey.all_sources))
        return CreatorSourceModel(
            journey.game_id, journey.game_title, journey.playthrough_id,
            journey.template.template_id,
            f"{journey.game_title} · прохождение №{journey.playthrough_sequence or 1}",
            journey.template.display_name, journey.status,
            journey.total_playtime_minutes, sources,
        )

    @staticmethod
    def _map(entry: JourneyEntry, index: int) -> CreatorSourceItem:
        return CreatorSourceItem(
            entry.source_id, entry.kind, entry.title, entry.body, entry.occurred_at,
            entry.stage_id, entry.rating, True, index,
            {"playthrough_sequence": entry.playthrough_sequence},
        )
