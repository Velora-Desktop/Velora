from collections.abc import Iterable
from typing import Any, TypeVar


T = TypeVar("T")


class AgeFilterService:
    """Keep adult-content policy outside widgets and catalog repositories."""

    @staticmethod
    def is_visible(age_rating: int | str | Any | None, hide_adult_content: bool) -> bool:
        """Return visibility for either a raw rating or a catalog object.

        Accepting both forms keeps the privacy filter safe during first-run and
        profile-reset flows, including older callers that pass ``GameData``.
        """
        if not hide_adult_content:
            return True
        value = getattr(age_rating, "age_rating", age_rating)
        try:
            normalized = int(str(value or 0).removesuffix("+"))
        except (TypeError, ValueError):
            normalized = 0
        return normalized < 18

    @classmethod
    def filter(cls, items: Iterable[T], hide_adult_content: bool) -> list[T]:
        return [
            item for item in items
            if cls.is_visible(getattr(item, "age_rating", 0), hide_adult_content)
        ]
