"""UI-neutral deterministic geometry policy for the AW0.23 Journey route."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JourneySegmentLayout:
    stage_id: str
    event_count: int
    visible_event_count: int
    hidden_event_count: int
    width: int


class JourneyTimelineLayoutModel:
    """Keeps widget layout and canvas geometry on the same event-count policy."""

    MAX_VISIBLE_EVENTS = 5
    EMPTY_WIDTH = 14
    EVENT_SLOT_WIDTH = 168
    OVERFLOW_SLOT_WIDTH = 48
    VISIBLE_TYPES = frozenset({
        "note", "impression", "screenshot", "achievement", "favorite",
        "favorite_moment", "challenge", "difficult", "difficult_moment",
        "music", "rating_change", "impression", "other", "legacy",
    })

    @classmethod
    def count_events(cls, stage) -> int:
        """Count only user-facing Timeline events for one mission."""
        return sum(
            1 for entry in stage.entries if entry.kind in cls.VISIBLE_TYPES
        )

    @classmethod
    def build(cls, stages) -> tuple[JourneySegmentLayout, ...]:
        result = []
        for stage in stages:
            count = cls.count_events(stage)
            visible = min(count, cls.MAX_VISIBLE_EVENTS)
            result.append(JourneySegmentLayout(
                stage.stage_id, count, visible, max(0, count - visible),
                cls.EMPTY_WIDTH if not count else (
                    visible * cls.EVENT_SLOT_WIDTH
                    + (cls.OVERFLOW_SLOT_WIDTH if count > visible else 0)
                ),
            ))
        return tuple(result)
