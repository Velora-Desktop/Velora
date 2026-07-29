from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from app.models.game import GameData
from app.ui.search.search_page import SearchPage
from app.ui.widgets.platform_icons import PlatformIconRow


def game(title: str, *, system_tags=(), tags=(), description="") -> GameData:
    return GameData(
        title, "8.0", "—", "НЕ НАЧИНАЛ", "Dev", "2020", "PC", "1P",
        description=description,
        catalog_id=title.casefold().replace(" ", "-"),
        system_tags=list(system_tags),
        tags=list(tags),
    )


class TagSearchUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_strict_tag_search_handles_hash_and_case(self):
        page = SearchPage()
        page.set_items([
            game("Doom Eternal", system_tags=("Демоны",)),
            game("Not a tag match", description="демоны"),
        ])
        page.set_tag_query("#ДЕМОНЫ")
        names = page.findChildren(QPushButton)
        self.assertEqual([button.text() for button in names], ["Doom Eternal"])
        page.deleteLater()

    def test_personal_tag_uses_same_search_path(self):
        page = SearchPage()
        page.set_items([game("Doom Eternal", tags=("Космос",))])
        page.set_tag_query(" космос ")
        self.assertEqual(
            [button.text() for button in page.findChildren(QPushButton)],
            ["Doom Eternal"],
        )
        page.search.clear()
        self.assertEqual(page._tag_query, "")
        page.deleteLater()

    def test_platform_parent_has_no_raw_identifier_tooltip(self):
        row = PlatformIconRow("PS4; Q13361286; Q19610114")
        self.assertEqual(row.toolTip(), "")
        tooltips = [
            label.toolTip() for label in row.findChildren(type(row._layout.itemAt(0).widget()))
            if label.toolTip()
        ]
        self.assertFalse(any(value.startswith("Q") for value in tooltips))
        row.deleteLater()


if __name__ == "__main__":
    unittest.main()
