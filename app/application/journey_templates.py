"""Universal, UI-neutral Journey template contracts for AW0.21."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class JourneyTemplate:
    template_id: str
    display_name: str
    description: str
    category: str
    supported_game_types: tuple[str, ...]
    base_structure: str
    stage_model: str
    checkpoint_model: str
    progress_model: str
    modifiers: tuple[str, ...]
    required_blocks: tuple[str, ...]
    optional_blocks: tuple[str, ...]
    creator_source_rules: tuple[str, ...]
    presentation_options: tuple[str, ...] = ()
    stage_titles: tuple[str, ...] = ()
    stage_ids: tuple[str, ...] = ()
    empty_state: str = "Начните прохождение — Journey сохранит его историю."


_SPECS = (
    ("story_campaign", "Story Campaign", "Сюжетное приключение с началом, развитием и финалом.", "Кампании", "mission", "chapter"),
    ("linear_campaign", "Linear Campaign", "Последовательная кампания по главам или уровням.", "Кампании", "chapter", "chapter"),
    ("open_world", "Open World", "Путешествие по регионам, линиям заданий и открытиям.", "Исследование", "region", "percent"),
    ("rpg", "RPG", "История персонажа, сюжетные арки, решения и развитие.", "Ролевые", "story_arc", "level"),
    ("metroidvania", "Metroidvania", "Новые способности, зоны и возвраты к прежним маршрутам.", "Исследование", "ability", "map"),
    ("arena_shooter", "Arena Shooter", "Арены, боевые встречи, испытания и боссы.", "Экшен", "encounter", "mission"),
    ("extraction_shooter", "Extraction Shooter", "Рейды, добыча, риск и успешные выходы.", "Сессии", "raid", "raid"),
    ("battle_royale", "Battle Royale", "Матчи, позиции, победы и сезонный прогресс.", "Сессии", "match", "season"),
    ("sandbox", "Sandbox", "Личные проекты, открытия и свободные игровые цели.", "Свободная игра", "project", "milestone"),
    ("survival", "Survival", "Дни выживания, убежище, ресурсы и переломные события.", "Свободная игра", "day", "milestone"),
    ("strategy", "Strategy", "Кампании, партии, решения и стратегические повороты.", "Стратегии", "turn", "campaign"),
    ("city_builder", "City Builder", "Этапы развития города, кризисы и достижения.", "Стратегии", "era", "population"),
    ("racing", "Racing", "Серии гонок, чемпионаты, машины и рекорды.", "Спорт и гонки", "event", "championship"),
    ("sports", "Sports", "Матчи, сезоны, турниры и личные рекорды.", "Спорт и гонки", "match", "season"),
    ("simulator", "Simulator", "Сессии, маршруты, проекты и развитие навыка.", "Симуляторы", "session", "hours"),
    ("puzzle", "Puzzle", "Головоломки, главы, открытия и моменты озарения.", "Головоломки", "puzzle", "chapter"),
    ("rhythm", "Rhythm", "Композиции, серии, сложность и личные рекорды.", "Ритм", "track", "score"),
    ("visual_novel", "Visual Novel", "Главы, маршруты, выборы и концовки.", "Истории", "chapter", "route"),
    ("interactive_movie", "Interactive Movie", "Сцены, решения, последствия и финалы.", "Истории", "scene", "branch"),
    ("mmorpg", "MMORPG", "Персонажи, сезоны, рейды, главы и долгий путь.", "Онлайн", "chapter", "level"),
    ("live_service", "Live Service", "Сезоны, события, обновления и возвращения.", "Онлайн", "season", "season"),
)


def _make(spec: tuple[str, str, str, str, str, str]) -> JourneyTemplate:
    template_id, name, description, category, stage, progress = spec
    return JourneyTemplate(
        template_id, name, description, category, ("game",),
        "timeline", stage, "start_middle_end", progress, (),
        ("summary", "stages", "checkpoints", "impressions"),
        ("key_moments", "ratings", "tags"),
        ("impressions", "checkpoints", "key_moments", "rating_changes", "conclusion"),
        ("compact_timeline", "automatic_creator_sources"),
    )


class JourneyTemplateRegistry:
    def __init__(self) -> None:
        self._items = {item.template_id: item for item in map(_make, _SPECS)}

    def all(self) -> tuple[JourneyTemplate, ...]:
        return tuple(self._items.values())

    def get(self, template_id: str) -> JourneyTemplate:
        return self._items[template_id]

    def resolve(self, *, title: str = "", category: str = "", subgroup: str = "") -> JourneyTemplate:
        haystack = f"{title} {category} {subgroup}".casefold()
        rules = (
            ("open world", "open_world"), ("rpg", "rpg"), ("гон", "racing"),
            ("стратег", "strategy"), ("симуля", "simulator"), ("выжива", "survival"),
            ("головол", "puzzle"), ("онлайн", "live_service"),
        )
        return self.get(next((value for key, value in rules if key in haystack), "story_campaign"))

    def from_payload(self, payload: dict | None) -> JourneyTemplate | None:
        """Resolve the official Studio payload; personal history never enters it."""
        if not isinstance(payload, dict) or payload.get("payload_version") != 1:
            return None
        template_id = str(payload.get("template_id") or "").strip()
        base = self._items.get(template_id)
        if base is None:
            return None
        visible_stages = tuple(
            item for item in payload.get("stages", ())
            if isinstance(item, dict)
            and bool(item.get("visible", True))
            and str(item.get("title") or "").strip()
        )
        stages = tuple(str(item.get("title") or "").strip() for item in visible_stages)
        stage_ids = tuple(
            str(item.get("stable_id") or item.get("stage_id") or f"stage-{index:02d}").strip()
            for index, item in enumerate(visible_stages, 1)
        )
        return replace(
            base,
            display_name=str(payload.get("name") or base.display_name),
            stage_titles=stages or base.stage_titles,
            stage_ids=stage_ids or base.stage_ids,
            optional_blocks=tuple(
                str(value) for value in payload.get("optional_blocks", ())
            ) or base.optional_blocks,
            presentation_options=tuple(
                str(value) for value in payload.get("quick_editor_fields", ())
            ) or base.presentation_options,
        )

    def doom_eternal(self) -> JourneyTemplate:
        return replace(
            self.get("story_campaign"),
            template_id="doom_eternal_reference",
            display_name="Doom Eternal · Story Arena Journey",
            description="Сюжетная кампания, рассказанная через миссии, арены, боссов и личные впечатления.",
            stage_model="mission",
            progress_model="mission",
            modifiers=("arena_shooter", "combat_encounters", "collectibles", "boss_moments"),
            optional_blocks=("key_moments", "ratings", "tags", "collectibles", "boss_moments"),
            stage_titles=(
                "Ад на Земле",
                "Ликование",
                "База сектантов",
                "База DOOM-охотников",
                "Кровавое супергнездо",
                "Комплекс Комитета",
                "Марс Ядро",
                "Сентинел Прайм",
                "Тарас Набад",
                "Некравол",
                "Некравол — часть II",
                "Урдак",
                "Последний грех",
            ),
        )
