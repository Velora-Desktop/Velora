import unittest

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

    def test_card_without_scores_has_no_empty_critic_grid(self) -> None:
        self.assertEqual(source_slots("Программы", {}, ""), [])


if __name__ == "__main__":
    unittest.main()
