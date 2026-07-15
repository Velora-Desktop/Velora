import unittest

from app.core.icon_registry import IconRegistry


class IconRegistryTests(unittest.TestCase):
    def test_all_approved_assets_exist(self) -> None:
        self.assertEqual(IconRegistry.validate_approved(), [])

    def test_unknown_icon_has_safe_fallback(self) -> None:
        self.assertIsNone(IconRegistry.path("definitely_missing_icon"))


if __name__ == "__main__":
    unittest.main()

