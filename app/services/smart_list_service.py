from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.personal_library import SmartListDefinition


class SmartListService:
    """Evaluate built-in and user-defined rules against live library objects."""

    BUILT_INS = (
        SmartListDefinition(None, "Без оценки", rules={"unrated": True}, is_system=True),
        SmartListDefinition(None, "Не начато", rules={"not_started": True}, is_system=True),
        SmartListDefinition(None, "Начато, но не закончено", rules={"in_progress": True}, is_system=True),
        SmartListDefinition(None, "Завершено", rules={"completed": True}, is_system=True),
        SmartListDefinition(None, "Брошено", rules={"dropped": True}, is_system=True),
        SmartListDefinition(None, "В избранном", rules={"favorite": True}, is_system=True),
        SmartListDefinition(None, "Оценка 9 и выше", rules={"personal_min": 9.0}, is_system=True),
        SmartListDefinition(None, "Давно не открывал", rules={"inactive_days": 180}, is_system=True),
        SmartListDefinition(None, "Недавно добавлено", rules={"added_days": 30}, is_system=True),
        SmartListDefinition(None, "Недавно изменено", rules={"changed_days": 14}, is_system=True),
        SmartListDefinition(None, "Перепройдено / пересмотрено", rules={"repeat": True}, is_system=True),
        SmartListDefinition(None, "Жду продолжения", rules={"waiting": True}, is_system=True),
        SmartListDefinition(None, "Без заметки", rules={"without_note": True}, is_system=True),
        SmartListDefinition(None, "Пользовательские карточки", rules={"source": "custom"}, is_system=True),
        SmartListDefinition(None, "Официальные карточки", rules={"source": "official"}, is_system=True),
    )

    COMPLETED = {"ПРОШЁЛ", "ПОСМОТРЕЛ", "ИСПОЛЬЗОВАЛ"}
    DROPPED = {"БРОСИЛ", "ОТКАЗАЛСЯ"}
    IN_PROGRESS = {"ПРОХОЖУ", "СМОТРЮ", "ИСПОЛЬЗУЮ"}

    @classmethod
    def filter(cls, items, definition: SmartListDefinition):
        return [item for item in items if cls.matches(item, definition.rules, definition.media_type)]

    @classmethod
    def matches(cls, item, rules: dict, media_type: str = "") -> bool:
        if media_type and item.media_type != media_type:
            return False
        if rules.get("unrated") and item.personal_score != "—": return False
        if rules.get("not_started") and item.user_interacted: return False
        if rules.get("in_progress") and item.status not in cls.IN_PROGRESS: return False
        if rules.get("completed") and item.status not in cls.COMPLETED: return False
        if rules.get("dropped") and item.status not in cls.DROPPED: return False
        if rules.get("favorite") and not item.favorite: return False
        if rules.get("waiting") and item.status != "ЖДУ НОВЫЙ СЕЗОН": return False
        if rules.get("without_note") and item.note.strip(): return False
        if rules.get("source") and item.source_type != rules["source"]: return False
        if rules.get("category") and item.category not in rules["category"]: return False
        if rules.get("subgroup") and item.subgroup not in rules["subgroup"]: return False
        if rules.get("tags") and not set(rules["tags"]).issubset(item.tags): return False
        if rules.get("repeat") and not (item.watch_count > 1 or any("повтор" in value.casefold() for value in item.history)): return False
        if rules.get("watch_count_min") is not None and item.watch_count < int(rules["watch_count_min"]): return False
        if rules.get("playtime_min") is not None and item.playtime_hours < float(rules["playtime_min"]): return False
        for key, value in (("personal_min", item.personal_score), ("personal_max", item.personal_score), ("general_min", item.general_score), ("general_max", item.general_score)):
            if rules.get(key) is None: continue
            try: score = float(value)
            except (TypeError, ValueError): return False
            if key.endswith("min") and score < float(rules[key]): return False
            if key.endswith("max") and score > float(rules[key]): return False
        now = datetime.now(timezone.utc)
        if rules.get("inactive_days") and cls._age_days(item.history[-1][:16] if item.history else "") < int(rules["inactive_days"]): return False
        if rules.get("added_days") and cls._age_days(item.interaction_started_at) > int(rules["added_days"]): return False
        if rules.get("changed_days") and cls._age_days(item.history[-1][:16] if item.history else "") > int(rules["changed_days"]): return False
        return True

    @staticmethod
    def _age_days(value: str) -> int:
        if not value: return 10_000
        for parser in (lambda: datetime.fromisoformat(value), lambda: datetime.strptime(value, "%d.%m.%Y %H:%M")):
            try:
                moment = parser()
                if moment.tzinfo is None: moment = moment.replace(tzinfo=timezone.utc)
                return max(0, (datetime.now(timezone.utc) - moment).days)
            except ValueError:
                continue
        return 10_000

    @staticmethod
    def describe(rules: dict) -> str:
        labels = {
            "unrated": "без оценки", "not_started": "не начато", "in_progress": "в процессе",
            "completed": "завершено", "dropped": "брошено", "favorite": "избранное",
            "waiting": "жду продолжения", "without_note": "без заметки", "repeat": "повтор",
        }
        parts = [label for key, label in labels.items() if rules.get(key)]
        for key, label in (("personal_min", "личная оценка от"), ("personal_max", "личная оценка до"), ("general_min", "общая оценка от"), ("general_max", "общая оценка до")):
            if rules.get(key) is not None: parts.append(f"{label} {rules[key]:g}")
        return " · ".join(parts) or "Все объекты"
