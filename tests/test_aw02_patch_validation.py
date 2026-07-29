from __future__ import annotations

import unittest

from velora_contracts.canonical_json import (
    canonical_json_bytes,
    manifest_content_sha256,
    sha256_bytes,
)
from velora_contracts.errors import ValidationError
from velora_contracts.validators import (
    validate_checksums,
    validate_media_manifest,
    validate_operation,
    validate_patch_manifest,
    validate_relative_path,
)


class PatchValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.checksums = {
            "database/operations.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "media_manifest.json": "5fccd4efbc76cd26c259df9c1a64e6396dd22de351bfbac0a41a9f702b610007",
        }
        self.manifest = {
            "allow_missing_deletes": False,
            "contracts_version": 1,
            "created_at": "2026-07-28T00:00:00Z",
            "dependencies": [],
            "from_catalog_version": "0.21",
            "manifest_version": 1,
            "minimum_app_version": "AW0.2",
            "operation_count": 0,
            "operation_file": "database/operations.jsonl",
            "patch_format_version": 1,
            "patch_id": "00000000-0000-4000-8000-000000000001",
            "to_catalog_version": "0.22",
        }
        self.manifest["content_sha256"] = manifest_content_sha256(
            self.checksums, self.manifest
        )

    def test_published_hash_fixture(self) -> None:
        self.assertEqual(
            canonical_json_bytes(
                {"entries": [], "media_manifest_version": 1}
            ).decode(),
            '{"entries":[],"media_manifest_version":1}',
        )
        self.assertEqual(
            self.manifest["content_sha256"],
            "7cf6f51a40096984edf27f67ae82a54eda34dec4c9b9452e6817aa117c99008a",
        )
        validate_checksums(self.checksums)
        validate_patch_manifest(self.manifest, self.checksums)

    def test_path_traversal_and_casefold_duplicates_are_rejected(self) -> None:
        for value in ("../user.db", "/absolute", "media\\cover.webp", "a//b"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_relative_path(value)
        with self.assertRaises(ValidationError):
            validate_checksums(
                {
                    "A/file": "0" * 64,
                    "a/FILE": "1" * 64,
                }
            )

    def test_media_manifest_contract(self) -> None:
        valid = {
            "media_manifest_version": 1,
            "entries": [
                {
                    "relative_path": "media/covers/a.webp",
                    "sha256": "0" * 64,
                    "byte_length": 10,
                    "mime_type": "image/webp",
                    "width": 100,
                    "height": 150,
                }
            ],
        }
        validate_media_manifest(valid)
        valid["entries"][0]["relative_path"] = "../escape.webp"
        with self.assertRaises(ValidationError):
            validate_media_manifest(valid)

    def test_operation_hash_and_unknown_fields(self) -> None:
        envelope = {
            "op_id": "11111111-1111-4111-8111-111111111111",
            "op_type": "item.upsert",
            "entity_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "payload": {
                "canonical_title": "Example",
                "lifecycle_state": "active",
                "media_type": "game",
                "sort_title": "example",
            },
        }
        operation = {
            **envelope,
            "content_sha256": sha256_bytes(canonical_json_bytes(envelope)),
        }
        validate_operation(operation, inserting=True)
        operation["payload"]["invented"] = True
        with self.assertRaises(ValidationError):
            validate_operation(operation, inserting=True)


if __name__ == "__main__":
    unittest.main()
