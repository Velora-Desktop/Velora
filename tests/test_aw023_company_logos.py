import json
import sqlite3
import unittest
from pathlib import Path
from xml.etree import ElementTree

from PySide6.QtWidgets import QApplication

from app.core.company_logos import resolve_company_logo, split_company_names
from app.core.icon_registry import IconRegistry
from app.ui.widgets.company_logo_row import CompanyLogoRow
from app.ui.quick_view.quick_view import QuickView
from app.models.game import GameData


ROOT = Path(__file__).resolve().parents[1]


class CompanyLogoPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.manifest = json.loads((ROOT / "assets/icons/company/company_logos_manifest.json").read_text(encoding="utf-8"))

    def test_semantic_ids_and_svg_files_resolve(self):
        for item in self.manifest["icons"]:
            path = IconRegistry.path(item["id"], variant="original", category="company")
            self.assertIsNotNone(path)
            ElementTree.parse(path)

    def test_reviewed_aliases_and_unknown(self):
        self.assertEqual(resolve_company_logo("EA"), "company.electronic_arts")
        self.assertEqual(resolve_company_logo("Electronic Arts Inc."), "company.electronic_arts")
        self.assertEqual(resolve_company_logo("Rockstar London"), "company.rockstar_games")
        self.assertEqual(resolve_company_logo("CD Projekt RED"), "company.cd_projekt_red")
        self.assertEqual(resolve_company_logo("Unknown Example Studio"), None)

    def test_mapping_has_no_duplicate_semantic_ids(self):
        ids = [item["id"] for item in self.manifest["icons"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_technical_wikidata_ids_never_reach_ui(self):
        self.assertEqual(
            split_company_names("Q830947; Rockstar London; Rockstar Vancouver"),
            ["Rockstar London", "Rockstar Vancouver"],
        )

    def test_missing_logo_safely_renders_plain_text(self):
        row = CompanyLogoRow()
        row.setText("Unknown Example Studio")
        labels = row.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        self.assertTrue(any(label.text() == "Unknown Example Studio" for label in labels))

    def test_compact_row_groups_subsidiaries_under_parent_logo(self):
        row = CompanyLogoRow(max_visible=1, compact=True)
        row.setText("Rockstar London; Rockstar Vancouver")
        labels = row.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        logo = next(label for label in labels if label.pixmap() and not label.pixmap().isNull())
        self.assertEqual(logo.toolTip(), "Rockstar London\nRockstar Vancouver")
        self.assertFalse(any(label.text() == "+1" for label in labels))
        self.assertFalse(any(label.text() == "Rockstar London" for label in labels))

    def test_full_metadata_resolves_max_payne_developer_list(self):
        row = CompanyLogoRow(max_visible=1)
        row.setText("Q830947; Rockstar London; Rockstar Vancouver")
        labels = row.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        self.assertTrue(any(label.pixmap() and not label.pixmap().isNull() for label in labels))
        self.assertFalse(any(label.text() == "Rockstar London" for label in labels))
        logo = next(label for label in labels if label.pixmap() and not label.pixmap().isNull())
        self.assertEqual(logo.toolTip(), "Rockstar London\nRockstar Vancouver")
        self.assertFalse(any(label.text() == "+1" for label in labels))
        self.assertFalse(any("Q830947" in label.text() for label in labels))

    def test_ea_black_box_is_grouped_under_ea_logo(self):
        row = CompanyLogoRow(max_visible=1)
        row.setText("Electronic Arts; EA Black Box")
        labels = row.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        logo = next(label for label in labels if label.pixmap() and not label.pixmap().isNull())
        self.assertEqual(logo.toolTip(), "Electronic Arts\nEA Black Box")
        self.assertFalse(any(label.text() == "+1" for label in labels))

    def test_resolved_company_name_is_tooltip_not_duplicate_text(self):
        row = CompanyLogoRow(max_visible=1)
        row.setText("CD Projekt RED")
        labels = row.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        logo = next(label for label in labels if label.pixmap() and not label.pixmap().isNull())
        self.assertEqual(logo.toolTip(), "CD Projekt RED")
        self.assertFalse(any(label.text() == "CD Projekt RED" for label in labels))
        self.assertGreaterEqual(logo.width(), 70)

    def test_quick_view_uses_raw_company_lists_for_both_roles(self):
        game = GameData(
            title="Max Payne 3", general_score="8.0", personal_score="—",
            status="НЕ НАЧИНАЛ", developer="Q830947; Rockstar London; Rockstar Vancouver",
            year="2012", platform="PC", mode="1P", catalog_id="g-test-company",
            publisher="Rockstar Games; Electronic Arts",
        )
        view = QuickView()
        view.set_game(game)
        developer_labels = view.developer.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        publisher_labels = view.publisher.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)
        self.assertTrue(any(label.pixmap() and not label.pixmap().isNull() for label in developer_labels))
        self.assertTrue(any(label.pixmap() and not label.pixmap().isNull() for label in publisher_labels))
        self.assertFalse(any("Q830947" in label.text() for label in developer_labels))

    def test_original_aspect_ratio_is_preserved(self):
        pixmap = IconRegistry.pixmap("company.electronic_arts", 60, 20, variant="original", category="company")
        self.assertLessEqual(pixmap.width(), 60)
        self.assertLessEqual(pixmap.height(), 20)

    def test_catalog_integrity(self):
        db = sqlite3.connect(ROOT / "data/catalog.db")
        self.assertEqual(db.execute("pragma integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
