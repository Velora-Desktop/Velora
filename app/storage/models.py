"""Typed persistence records crossing repository boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from velora_contracts.enums import (
    CatalogLifecycleState,
    LibraryMembershipState,
    MediaType,
    RatingType,
    SourceType,
)


@dataclass(frozen=True, slots=True)
class SchemaMetadata:
    schema_version: int
    contract_version: int
    core_generation: int
    reset_boundary: str | None
    reset_operation_id: str | None
    reset_state: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class CatalogItem:
    catalog_id: str
    media_type: MediaType
    canonical_title: str
    sort_title: str
    release_year: int | None
    short_description: str | None
    description: str | None
    lifecycle_state: CatalogLifecycleState
    revision: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class UserItem:
    user_item_id: str
    media_type: MediaType
    title: str
    release_year: int | None
    description: str | None
    created_at: str
    updated_at: str
    is_archived: bool


@dataclass(frozen=True, slots=True)
class LibraryState:
    source_type: SourceType
    item_id: str
    membership_state: LibraryMembershipState
    favorite: bool
    projected_status: str | None
    projected_progress_value: float | None
    projected_progress_unit: str | None
    projected_total_playtime_minutes: int
    started_at: str | None
    completed_at: str | None
    archived_at: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class Playthrough:
    playthrough_id: str
    source_type: SourceType
    item_id: str
    sequence_no: int
    status: str
    started_at: str | None
    ended_at: str | None
    playtime_minutes: int
    progress_value: float | None
    progress_unit: str | None
    is_current: bool
    deleted_at: str | None


@dataclass(frozen=True, slots=True)
class JourneyEvent:
    event_id: str
    operation_id: str
    source_type: SourceType
    item_id: str
    playthrough_id: str | None
    event_type: str
    payload_version: int
    payload_json: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class Rating:
    rating_id: str
    source_type: SourceType
    item_id: str
    playthrough_id: str | None
    rating_type: RatingType
    checkpoint_type: str | None
    value_tenths: int | None
    review_text: str | None
    is_current: bool
    superseded_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class Impression:
    impression_id: str
    playthrough_id: str
    checkpoint_type: str | None
    text: str
    progress_value: float | None
    progress_unit: str | None
    playtime_minutes_at_entry: int | None
    created_at: str


@dataclass(frozen=True, slots=True)
class Tag:
    tag_id: str
    name: str


@dataclass(frozen=True, slots=True)
class UserTag:
    node_id: str
    name: str
