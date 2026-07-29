"""Canonical JSON Serializer v1 and SHA-256 helpers."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import ValidationError


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("NaN and Infinity are forbidden")
        raise ValidationError("Non-integer numbers are forbidden in canonical JSON")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError("Canonical JSON object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise ValidationError("Duplicate object key after NFC normalization")
            normalized[normalized_key] = _normalize(item)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [_normalize(item) for item in value]
    raise ValidationError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_text(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_content_sha256(checksums: Mapping[str, str], manifest: Mapping[str, Any]) -> str:
    without_hash = dict(manifest)
    without_hash.pop("content_sha256", None)
    payload = bytearray()
    for path in sorted(checksums):
        payload.extend(path.encode("utf-8"))
        payload.append(0)
        payload.extend(checksums[path].lower().encode("ascii"))
        payload.append(10)
    payload.extend(canonical_json_bytes(without_hash))
    return sha256_bytes(bytes(payload))
