"""Content-neutral value objects shared by Velora and Studio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .enums import SourceType, UnresolvedReason
from .errors import ValidationError
from .ids import CatalogId, UserItemId


@dataclass(frozen=True, slots=True)
class CatalogItemRef:
    source_type: SourceType
    item_id: str

    def __post_init__(self) -> None:
        source = SourceType(self.source_type)
        object.__setattr__(self, "source_type", source)
        if source is SourceType.OFFICIAL:
            CatalogId(self.item_id)
        else:
            UserItemId(self.item_id)

    def to_dict(self) -> dict[str, str]:
        return {"source_type": self.source_type.value, "item_id": self.item_id}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CatalogItemRef":
        if set(value) != {"source_type", "item_id"}:
            raise ValidationError("CatalogItemRef contains missing or unknown fields")
        try:
            return cls(SourceType(value["source_type"]), str(value["item_id"]))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid CatalogItemRef") from exc


@dataclass(frozen=True, slots=True)
class UnresolvedOfficialRef:
    catalog_id: str
    reason: UnresolvedReason
    last_known_title: str | None = None

    def __post_init__(self) -> None:
        CatalogId(self.catalog_id)
        object.__setattr__(self, "reason", UnresolvedReason(self.reason))
