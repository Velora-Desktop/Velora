"""Pure validators for Patch Format 1 packages."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID

from .canonical_json import canonical_json_bytes, manifest_content_sha256, sha256_bytes
from .errors import ValidationError

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*$")

MANIFEST_FIELDS = {
    "manifest_version",
    "patch_format_version",
    "patch_id",
    "from_catalog_version",
    "to_catalog_version",
    "contracts_version",
    "minimum_app_version",
    "created_at",
    "operation_file",
    "operation_count",
    "allow_missing_deletes",
    "dependencies",
    "content_sha256",
}
MEDIA_ENTRY_FIELDS = {
    "relative_path",
    "sha256",
    "byte_length",
    "mime_type",
    "width",
    "height",
}
OPERATION_REQUIRED_FIELDS = {
    "op_id",
    "op_type",
    "entity_id",
    "payload",
    "content_sha256",
}
OPERATION_OPTIONAL_FIELDS = {"expected_revision"}

OPERATION_CONTRACTS: dict[str, tuple[set[str], set[str]]] = {
    "item.upsert": (
        {"media_type", "canonical_title", "sort_title", "lifecycle_state"},
        {"release_year", "short_description", "description"},
    ),
    "item.retire": ({"lifecycle_state", "reason"}, set()),
    "title.upsert": (
        {"catalog_id", "title", "title_type", "is_searchable"},
        {"language_code", "region_code"},
    ),
    "title.delete": (set(), set()),
    "company.upsert": ({"canonical_name", "display_name", "is_active"}, set()),
    "company_link.upsert": ({"catalog_id", "company_id", "role_id"}, {"release_id"}),
    "company_link.delete": (set(), set()),
    "release.upsert": (
        {"catalog_id", "release_precision", "is_primary"},
        {"platform_id", "region_code", "release_date", "edition_name"},
    ),
    "release.delete": (set(), set()),
    "edition.upsert": (
        {"catalog_id", "canonical_name", "display_name", "edition_type", "is_primary"},
        {"release_id", "description"},
    ),
    "edition.delete": (set(), set()),
    "addon.upsert": (
        {"parent_catalog_id", "canonical_name", "display_name", "addon_type"},
        {"addon_catalog_id", "release_date", "description"},
    ),
    "addon.delete": (set(), set()),
    "genre.upsert": ({"canonical_name", "display_name", "is_active"}, set()),
    "tag.upsert": ({"canonical_name", "display_name", "is_active"}, set()),
    "genre_link.set": ({"genre_ids"}, set()),
    "tag_link.set": ({"tag_ids"}, set()),
    "relation.upsert": (
        {"source_catalog_id", "target_catalog_id", "relation_type"},
        {"series_order_milli", "story_order_milli", "note"},
    ),
    "relation.delete": (set(), set()),
    "redirect.upsert": ({"target_catalog_id", "reason"}, set()),
    "rating_observation.upsert": (
        {
            "catalog_id",
            "rating_kind",
            "source_name",
            "raw_value_milli",
            "raw_scale_max_milli",
            "normalized_value_tenths",
            "observed_at",
            "is_current",
        },
        {"vote_count", "source_url"},
    ),
    "duration.upsert": (
        set(),
        {
            "main_story_minutes",
            "main_extra_minutes",
            "completionist_minutes",
            "source_name",
            "observed_at",
        },
    ),
    "image.upsert": (
        {
            "catalog_id",
            "image_role",
            "variant",
            "relative_path",
            "width",
            "height",
            "format",
            "checksum_sha256",
            "is_primary",
        },
        set(),
    ),
    "image.delete": ({"remove_media_if_unreferenced"}, set()),
}

EMPTY_DELETE_OPERATIONS = frozenset(
    name for name in OPERATION_CONTRACTS if name.endswith(".delete") and name != "image.delete"
)
SET_OPERATIONS = frozenset({"genre_link.set", "tag_link.set"})


def _uuid(value: Any, field: str) -> None:
    try:
        parsed = UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError(f"{field} must be a canonical UUID") from exc
    if str(parsed) != value:
        raise ValidationError(f"{field} must be a lowercase canonical UUID")


def validate_relative_path(value: Any, *, media_only: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError("Path must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise ValidationError("Path must be NFC-normalized")
    if "\\" in value or value.startswith("/") or "\x00" in value:
        raise ValidationError(f"Unsafe package path: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValidationError(f"Unsafe package path: {value!r}")
    if media_only and (not parts or parts[0] != "media"):
        raise ValidationError("Media path must be inside media/")
    return value


def validate_unique_paths(paths: Iterable[str]) -> None:
    folded: set[str] = set()
    for path in paths:
        safe = validate_relative_path(path)
        key = safe.casefold()
        if key in folded:
            raise ValidationError(f"Duplicate package path after case-folding: {safe}")
        folded.add(key)


def validate_checksums(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValidationError("checksums.json must be an object")
    validate_unique_paths(value.keys())
    result: dict[str, str] = {}
    for path, digest in value.items():
        if path in {"manifest.json", "checksums.json"}:
            raise ValidationError(f"{path} must not be listed in checksums.json")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValidationError(f"Invalid SHA-256 for {path}")
        result[path] = digest
    return result


def validate_patch_manifest(value: Any, checksums: Mapping[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != MANIFEST_FIELDS:
        raise ValidationError("Patch manifest contains missing or unknown fields")
    if value["manifest_version"] != 1 or value["patch_format_version"] != 1:
        raise ValidationError("Unsupported patch manifest/format version")
    if value["contracts_version"] != 1:
        raise ValidationError("Unsupported contracts version")
    _uuid(value["patch_id"], "patch_id")
    if not VERSION_RE.fullmatch(str(value["from_catalog_version"])):
        raise ValidationError("Invalid from_catalog_version")
    if not VERSION_RE.fullmatch(str(value["to_catalog_version"])):
        raise ValidationError("Invalid to_catalog_version")
    if value["minimum_app_version"] != "AW0.2":
        raise ValidationError("Patch requires an unsupported application baseline")
    if value["operation_file"] != "database/operations.jsonl":
        raise ValidationError("Unsupported operation_file")
    if not isinstance(value["operation_count"], int) or value["operation_count"] < 0:
        raise ValidationError("operation_count must be a non-negative integer")
    if not isinstance(value["allow_missing_deletes"], bool):
        raise ValidationError("allow_missing_deletes must be boolean")
    if not isinstance(value["dependencies"], list) or len(set(value["dependencies"])) != len(value["dependencies"]):
        raise ValidationError("dependencies must be a unique array")
    if not isinstance(value["content_sha256"], str) or not SHA256_RE.fullmatch(value["content_sha256"]):
        raise ValidationError("Invalid manifest content_sha256")
    if checksums is not None:
        expected = manifest_content_sha256(checksums, value)
        if value["content_sha256"] != expected:
            raise ValidationError("Manifest content_sha256 mismatch")
    canonical_json_bytes(value)
    return dict(value)


def validate_media_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"media_manifest_version", "entries"}:
        raise ValidationError("Media manifest contains missing or unknown fields")
    if value["media_manifest_version"] != 1 or not isinstance(value["entries"], list):
        raise ValidationError("Unsupported media manifest")
    paths: list[str] = []
    previous = ""
    for entry in value["entries"]:
        if not isinstance(entry, dict) or set(entry) != MEDIA_ENTRY_FIELDS:
            raise ValidationError("Media entry contains missing or unknown fields")
        path = validate_relative_path(entry["relative_path"], media_only=True)
        if previous and path <= previous:
            raise ValidationError("Media entries must be sorted by relative_path")
        previous = path
        paths.append(path)
        if not isinstance(entry["sha256"], str) or not SHA256_RE.fullmatch(entry["sha256"]):
            raise ValidationError(f"Invalid media SHA-256: {path}")
        if not isinstance(entry["byte_length"], int) or entry["byte_length"] < 0:
            raise ValidationError(f"Invalid media byte_length: {path}")
        mime = entry["mime_type"]
        if not isinstance(mime, str) or "/" not in mime:
            raise ValidationError(f"Invalid media MIME type: {path}")
        is_image = mime.startswith("image/")
        dimensions = (entry["width"], entry["height"])
        if is_image and (
            not all(isinstance(item, int) and item > 0 for item in dimensions)
        ):
            raise ValidationError(f"Image dimensions are required: {path}")
        if not is_image and any(item is not None for item in dimensions):
            raise ValidationError(f"Dimensions are forbidden for non-image media: {path}")
    validate_unique_paths(paths)
    canonical_json_bytes(value)
    return dict(value)


def validate_operation(value: Any, *, inserting: bool | None = None) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or not OPERATION_REQUIRED_FIELDS.issubset(value)
        or set(value) - OPERATION_REQUIRED_FIELDS - OPERATION_OPTIONAL_FIELDS
    ):
        raise ValidationError("Operation contains missing or unknown fields")
    _uuid(value["op_id"], "op_id")
    op_type = value["op_type"]
    if op_type not in OPERATION_CONTRACTS:
        raise ValidationError(f"Unknown operation: {op_type}")
    if not isinstance(value["entity_id"], str) or not value["entity_id"]:
        raise ValidationError("entity_id is required")
    revision = value.get("expected_revision")
    if revision is not None and (not isinstance(revision, int) or revision < 1):
        raise ValidationError("expected_revision must be a positive integer or null")
    if op_type in SET_OPERATIONS and revision is not None:
        raise ValidationError("Set replacement expected_revision must be null")
    if inserting is True and revision is not None:
        raise ValidationError("Guaranteed inserts must omit expected_revision as null")
    if inserting is False and op_type not in SET_OPERATIONS and revision is None:
        raise ValidationError("Update/delete requires expected_revision")
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise ValidationError("Operation payload must be an object")
    required, optional = OPERATION_CONTRACTS[op_type]
    unknown = set(payload) - required - optional
    if unknown:
        raise ValidationError(f"Unknown payload fields for {op_type}: {sorted(unknown)}")
    if inserting is True and not required.issubset(payload):
        raise ValidationError(f"Missing insert fields for {op_type}: {sorted(required - set(payload))}")
    if op_type in EMPTY_DELETE_OPERATIONS and payload:
        raise ValidationError(f"{op_type} payload must be empty")
    if op_type == "duration.upsert" and not any(
        name in payload
        for name in ("main_story_minutes", "main_extra_minutes", "completionist_minutes")
    ):
        raise ValidationError("duration.upsert requires at least one duration")
    if op_type in SET_OPERATIONS:
        key = "genre_ids" if op_type.startswith("genre") else "tag_ids"
        maximum = 64 if key == "genre_ids" else 256
        ids = payload.get(key)
        if not isinstance(ids, list) or len(ids) > maximum or len(set(ids)) != len(ids):
            raise ValidationError(f"{key} must be a unique array with at most {maximum} IDs")
        for item in ids:
            _uuid(item, key)
    digest = value["content_sha256"]
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ValidationError("Invalid operation content_sha256")
    envelope = dict(value)
    envelope.pop("content_sha256")
    if sha256_bytes(canonical_json_bytes(envelope)) != digest:
        raise ValidationError("Operation content_sha256 mismatch")
    return dict(value)
