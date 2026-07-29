"""Pure typed projections for future Games UI consumers."""

from __future__ import annotations

from dataclasses import dataclass

from velora_contracts.enums import LibraryMembershipState
from velora_contracts.value_objects import CatalogItemRef


@dataclass(frozen=True, slots=True)
class GameRowReadModel:
    user_item_id: str | None
    catalog_item_ref: CatalogItemRef
    title: str
    library_lifecycle_state: LibraryMembershipState
    current_playthrough_id: str | None
    playthrough_status: str | None
    total_playtime_minutes: int
    current_checkpoint: str | None
    current_personal_rating_tenths: int | None
    latest_impression_preview: str | None
    updated_at: str
