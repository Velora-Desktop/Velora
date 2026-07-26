from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SmartListDefinition:
    list_id: int | None
    name: str
    media_type: str = ""
    rules: dict = field(default_factory=dict)
    is_system: bool = False


@dataclass(slots=True)
class UserGoal:
    goal_id: int | None
    title: str
    metric: str
    target_value: float
    current_value: float = 0.0
    media_type: str = ""
    deadline: str = ""
    completed_at: str = ""


@dataclass(slots=True)
class ActivityEntry:
    activity_id: int
    catalog_id: str
    event_type: str
    old_value: str
    new_value: str
    note: str
    created_at: str


@dataclass(slots=True)
class ManualList:
    list_id: int | None
    name: str
    description: str = ""
    cover_path: str = ""
    is_ranked: bool = False
    is_pinned: bool = False


@dataclass(slots=True)
class QueueEntry:
    catalog_id: str
    position: int
    plan_kind: str = "Без даты"
    planned_date: str = ""
    priority: str = "Обычный"
    reason: str = ""
    goal_id: int | None = None


@dataclass(slots=True)
class ReviewDraft:
    catalog_id: str
    title: str = ""
    body: str = ""
    criteria: dict = field(default_factory=dict)
    template_id: int | None = None
    updated_at: str = ""
