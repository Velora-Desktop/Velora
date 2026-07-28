import json
import sqlite3
import unittest
from pathlib import Path

from app.ui.widgets.critic_sources import source_slots


class CriticSourceSlotsTest(unittest.TestCase):
    def test_game_cards_have_stable_count(self) -> None:
        slots = source_slots("Игры", {"Metacritic": 7.3}, "Metacritic")
        self.assertEqual(
            slots,
            [
                ("Metacritic", 7.3),
                ("IGN", None),
                ("DualShockers", None),
                ("PC Gamer", None),
            ],
        )

    def test_imdb_priority_is_not_written_into_caption(self) -> None:
        slots = source_slots("Фильмы", {"IMDb": 8.6}, "IMDb")
        self.assertEqual(slots[0], ("IMDb", 8.6))
        self.assertTrue(all("главн" not in name.casefold() for name, _value in slots))
        self.assertEqual(len(slots), 4)

    def test_actual_non_default_source_is_preserved(self) -> None:
        slots = source_slots("Игры", {"GameSpot": 8.0}, "GameSpot")
        self.assertEqual(slots[0], ("GameSpot", 8.0))
        self.assertEqual(len(slots), 4)

    def test_catalog_order_is_not_changed_by_legacy_primary_source(self) -> None:
        scores = {
            "Metacritic": 8.0,
            "IGN": 9.0,
            "DualShockers": 7.0,
            "PC Gamer": 8.5,
        }
        slots = source_slots("Игры", scores, "PC Gamer")
        self.assertEqual(
            [name for name, _value in slots],
            ["Metacritic", "IGN", "DualShockers", "PC Gamer"],
        )

    def test_card_without_scores_has_no_empty_critic_grid(self) -> None:
        self.assertEqual(source_slots("Программы", {}, ""), [])

    def test_game_catalog_uses_standard_source_order_and_no_primary_marker(self) -> None:
        connection = sqlite3.connect(Path(__file__).parents[1] / "data" / "catalog.db")
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT critic_scores_json,primary_critic_source FROM catalog_items "
                "WHERE catalog_id LIKE 'g-%'"
            ).fetchall()
        finally:
            connection.close()
        canonical = ["Metacritic", "IGN", "DualShockers", "PC Gamer"]
        for row in rows:
            names = list(json.loads(row["critic_scores_json"] or "{}"))
            standard = [name for name in canonical if name in names]
            self.assertEqual(standard, names[:len(standard)])
            self.assertEqual("", row["primary_critic_source"])


if __name__ == "__main__":
    unittest.main()
