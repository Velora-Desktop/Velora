from __future__ import annotations

import random
from collections import Counter


class LibraryRecommendationService:
    """Explainable, offline selection from objects already present in the library."""

    PRIORITY = {"Высокий": 30, "Обычный": 15, "Низкий": 5}

    @classmethod
    def recommend(cls, items, queue, *, media_type: str = "", only_unstarted: bool = True):
        by_id={item.catalog_id:item for item in items}; interacted=[item for item in items if item.user_interacted and item.personal_score!="—"]
        favorite_categories=Counter(item.category for item in interacted if float(item.personal_score)>=8)
        candidates=[]
        for entry in queue:
            item=by_id.get(entry.catalog_id)
            if not item or (media_type and item.media_type!=media_type):continue
            if only_unstarted and item.user_interacted:continue
            score=cls.PRIORITY.get(entry.priority,10);reasons=[f"приоритет в очереди: {entry.priority.lower()}"]
            if favorite_categories[item.category]:score+=favorite_categories[item.category]*3;reasons.append("категория часто получает у вас высокие оценки")
            if entry.goal_id:score+=10;reasons.append("объект связан с активной целью")
            if entry.planned_date:score+=5;reasons.append("для объекта указана планируемая дата")
            candidates.append((score,item,reasons))
        if not candidates:return None,[]
        _,item,reasons=max(candidates,key=lambda value:value[0]);return item,reasons

    @staticmethod
    def random_choice(items, queue, *, media_type: str = "", only_queue: bool = True, exclude_dropped: bool = True):
        queued={entry.catalog_id for entry in queue};values=[]
        for item in items:
            if media_type and item.media_type!=media_type:continue
            if only_queue and item.catalog_id not in queued:continue
            if exclude_dropped and item.status in ("БРОСИЛ","ОТКАЗАЛСЯ"):continue
            values.append(item)
        return random.SystemRandom().choice(values) if values else None

    @staticmethod
    def queue_duration(items, queue) -> tuple[int,int | None]:
        by_id={item.catalog_id:item for item in items};minutes=0;known=0
        for entry in queue:
            item=by_id.get(entry.catalog_id)
            if item and item.duration_minutes:minutes+=item.duration_minutes;known+=1
        return len(queue), minutes if known==len(queue) and queue else None
