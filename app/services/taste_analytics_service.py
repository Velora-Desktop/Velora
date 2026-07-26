from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone


class TasteAnalyticsService:
    @staticmethod
    def score_comparison(items) -> dict:
        values = []
        for item in items:
            try: values.append((item, float(item.personal_score) - float(item.general_score)))
            except (TypeError, ValueError): continue
        values.sort(key=lambda pair: pair[1])
        return {
            "average_delta": sum(delta for _, delta in values) / len(values) if values else 0.0,
            "higher": list(reversed(values[-5:])),
            "lower": values[:5],
            "agreement": sum(abs(delta) <= 1 for _, delta in values) / len(values) * 100 if values else 0.0,
        }

    @staticmethod
    def periods(activities: list[dict], days: int = 30) -> dict:
        now = datetime.now(timezone.utc); current_start = now - timedelta(days=days); previous_start = current_start - timedelta(days=days)
        current = [row for row in activities if TasteAnalyticsService._moment(row.get("created_at")) >= current_start]
        previous = [row for row in activities if previous_start <= TasteAnalyticsService._moment(row.get("created_at")) < current_start]
        return {"days": days, "current": len(current), "previous": len(previous), "delta": len(current) - len(previous)}

    @staticmethod
    def _moment(value) -> datetime:
        try:
            moment = datetime.fromisoformat(str(value))
            return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
