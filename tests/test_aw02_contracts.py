from __future__ import annotations

import unittest

from velora_contracts.canonical_json import canonical_json_bytes
from velora_contracts.enums import SourceType
from velora_contracts.errors import ValidationError
from velora_contracts.events import DomainEvent
from velora_contracts.ids import CatalogId, EventId, OperationId
from velora_contracts.value_objects import CatalogItemRef


CATALOG_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EVENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
OPERATION_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


class ContractTests(unittest.TestCase):
    def test_catalog_ref_round_trip(self) -> None:
        original = CatalogItemRef(SourceType.OFFICIAL, CATALOG_ID)
        self.assertEqual(CatalogItemRef.from_dict(original.to_dict()), original)

    def test_event_round_trip(self) -> None:
        original = DomainEvent(
            event_name="LibraryItemAdded.v1",
            event_id=EventId(EVENT_ID),
            operation_id=OperationId(OPERATION_ID),
            occurred_at="2026-07-28T00:00:00Z",
            subject_ref=CatalogItemRef(SourceType.OFFICIAL, CATALOG_ID),
            changed_fields=("membership_state",),
            data={"membership_state": "active"},
        )
        self.assertEqual(DomainEvent.from_dict(original.to_dict()), original)

    def test_invalid_identifier_and_event_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CatalogId("NOT-A-UUID")
        with self.assertRaises(ValidationError):
            CatalogId(CATALOG_ID.upper())
        with self.assertRaises(ValidationError):
            DomainEvent(
                event_name="InventedEvent.v1",
                event_id=EventId(EVENT_ID),
                operation_id=OperationId(OPERATION_ID),
                occurred_at="2026-07-28T00:00:00Z",
            )

    def test_canonical_json_normalizes_strings_and_rejects_floats(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"z": "e\u0301", "a": [True, None, 3]}),
            '{"a":[true,null,3],"z":"é"}'.encode(),
        )
        with self.assertRaises(ValidationError):
            canonical_json_bytes({"rating": 8.5})


if __name__ == "__main__":
    unittest.main()
