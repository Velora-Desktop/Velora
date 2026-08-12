"""Stable Journey mood identifiers and their presentation metadata."""
from __future__ import annotations

from dataclasses import dataclass

from app.ui.velora_ui.theme.tokens import Colors


@dataclass(frozen=True, slots=True)
class MoodDefinition:
    id: str
    display_name: str
    short_name: str
    tooltip: str
    score_weight: int
    color: str
    icon_key: str


class MoodRegistry:
    _items = (
        MoodDefinition("excited", "Восторг", "Восторг", "Сильный восторг", 5, Colors.MOOD_EXCITED, "mood.excited"),
        MoodDefinition("happy", "Радость", "Радость", "Положительные эмоции", 4, Colors.MOOD_HAPPY, "mood.happy"),
        MoodDefinition("positive", "Позитив", "Позитив", "Скорее положительно", 3, Colors.MOOD_POSITIVE, "mood.positive"),
        MoodDefinition("neutral", "Нейтрально", "Нейтрально", "Без выраженной эмоции", 2, Colors.MOOD_NEUTRAL, "mood.neutral"),
        MoodDefinition("tired", "Усталость", "Усталость", "Этап утомил", 1, Colors.MOOD_TIRED, "mood.tired"),
        MoodDefinition("bored", "Скука", "Скука", "Этап показался скучным", 0, Colors.MOOD_BORED, "mood.bored"),
        MoodDefinition("disappointed", "Разочарование", "Разочарование", "Ожидания не оправдались", -1, Colors.MOOD_DISAPPOINTED, "mood.disappointed"),
        MoodDefinition("angry", "Злость", "Злость", "Этап вызвал раздражение", -2, Colors.MOOD_ANGRY, "mood.angry"),
    )
    _by_id = {item.id: item for item in _items}

    @classmethod
    def all(cls) -> tuple[MoodDefinition, ...]:
        return cls._items

    @classmethod
    def get(cls, mood_id: str | None) -> MoodDefinition | None:
        return cls._by_id.get(mood_id or "")

    @classmethod
    def require(cls, mood_id: str) -> MoodDefinition:
        try:
            return cls._by_id[mood_id]
        except KeyError as exc:
            raise ValueError(f"Unknown mood id: {mood_id}") from exc
