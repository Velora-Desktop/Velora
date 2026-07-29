"""Opaque lowercase UUID identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4

from .errors import ValidationError


@dataclass(frozen=True, slots=True)
class TypedId:
    value: str

    def __post_init__(self) -> None:
        try:
            parsed = UUID(self.value)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid {type(self).__name__}: expected UUID") from exc
        canonical = str(parsed)
        if self.value != canonical:
            raise ValidationError(
                f"Invalid {type(self).__name__}: UUID must use lowercase canonical form"
            )

    @classmethod
    def new(cls) -> Self:
        return cls(str(uuid4()))

    def __str__(self) -> str:
        return self.value


class CatalogId(TypedId):
    pass


class UserItemId(TypedId):
    pass


class OperationId(TypedId):
    pass


class EventId(TypedId):
    pass


class PlaythroughId(TypedId):
    pass


class RatingId(TypedId):
    pass


class AchievementId(TypedId):
    pass


class SnapshotId(TypedId):
    pass
