"""Versioned post-commit notification payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .errors import ValidationError
from .ids import EventId, OperationId
from .value_objects import CatalogItemRef


EVENT_NAMES = frozenset(
    {
        "LibraryItemAdded.v1",
        "LibraryItemArchived.v1",
        "LibraryItemRestored.v1",
        "PlaythroughStarted.v1",
        "PlaythroughStatusChanged.v1",
        "PlaytimeAdded.v1",
        "ProgressChanged.v1",
        "ImpressionAdded.v1",
        "ImpressionEdited.v1",
        "CheckpointSaved.v1",
        "FinalRatingSaved.v1",
        "ItemLinked.v1",
        "ItemUnlinked.v1",
        "AchievementUnlocked.v1",
        "PatchApplied.v1",
        "BackupCreated.v1",
        "RestoreCompleted.v1",
    }
)


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_name: str
    event_id: EventId
    operation_id: OperationId
    occurred_at: str
    subject_ref: CatalogItemRef | None = None
    playthrough_id: str | None = None
    changed_fields: tuple[str, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)
    event_version: int = 1

    def __post_init__(self) -> None:
        if self.event_name not in EVENT_NAMES:
            raise ValidationError(f"Unknown Contracts 1 event: {self.event_name}")
        if self.event_version != 1 or not self.event_name.endswith(".v1"):
            raise ValidationError("Event name/version mismatch")
        if not self.occurred_at:
            raise ValidationError("occurred_at is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_name": self.event_name,
            "event_version": self.event_version,
            "event_id": str(self.event_id),
            "operation_id": str(self.operation_id),
            "occurred_at": self.occurred_at,
            "subject_ref": self.subject_ref.to_dict() if self.subject_ref else None,
            "playthrough_id": self.playthrough_id,
            "changed_fields": list(self.changed_fields),
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DomainEvent":
        expected = {
            "event_name",
            "event_version",
            "event_id",
            "operation_id",
            "occurred_at",
            "subject_ref",
            "playthrough_id",
            "changed_fields",
            "data",
        }
        if set(value) != expected:
            raise ValidationError("DomainEvent contains missing or unknown fields")
        ref = value["subject_ref"]
        return cls(
            event_name=str(value["event_name"]),
            event_version=int(value["event_version"]),
            event_id=EventId(str(value["event_id"])),
            operation_id=OperationId(str(value["operation_id"])),
            occurred_at=str(value["occurred_at"]),
            subject_ref=CatalogItemRef.from_dict(ref) if ref is not None else None,
            playthrough_id=value["playthrough_id"],
            changed_fields=tuple(str(item) for item in value["changed_fields"]),
            data=dict(value["data"]),
        )
