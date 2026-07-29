import tempfile
import unittest
from pathlib import Path

from app.storage.migrations import discover_migrations
from velora_contracts.errors import ValidationError


class MigrationDiscoveryTests(unittest.TestCase):
    def test_discovers_contiguous_immutable_inputs_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "001_schema_one.sql").write_text("SELECT 1;", encoding="utf-8")
            (root / "002_schema_two.sql").write_text("SELECT 2;", encoding="utf-8")
            values = discover_migrations(root)
            self.assertEqual([value.order for value in values], [1, 2])
            self.assertEqual(len(values[0].checksum_sha256), 64)

    def test_rejects_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "001_one.sql").write_text("SELECT 1;", encoding="utf-8")
            (root / "003_three.sql").write_text("SELECT 3;", encoding="utf-8")
            with self.assertRaises(ValidationError):
                discover_migrations(root)


if __name__ == "__main__":
    unittest.main()
