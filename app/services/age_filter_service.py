from collections.abc import Iterable
from typing import TypeVar


T = TypeVar("T")


class AgeFilterService:
    """Keep adult-content policy outside widgets and catalog repositories."""

    @staticmethod
    def is_visible(age_rating: int | None, hide_adult_content: bool) -> bool:
        return not hide_adult_content or int(age_rating or 0) < 18

    @classmethod
    def filter(cls, items: Iterable[T], hide_adult_content: bool) -> list[T]:
        return [
            item for item in items
            if cls.is_visible(getattr(item, "age_rating", 0), hide_adult_content)
        ]
