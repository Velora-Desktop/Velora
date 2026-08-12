import unittest

from app.ui.rating_palette import MISSING_RATING_COLOR, rating_color


class RatingPaletteTests(unittest.TestCase):
    def test_scale_has_red_yellow_green_anchors(self) -> None:
        self.assertEqual(rating_color(0), "#FF4545")
        self.assertEqual(rating_color(5), "#FFC52E")
        self.assertEqual(rating_color(10), "#20D874")

    def test_intermediate_scores_use_distinct_gradient_colours(self) -> None:
        colours = [rating_color(score) for score in (2.5, 5, 7.5, 9.6)]
        self.assertEqual(len(colours), len(set(colours)))

    def test_invalid_or_missing_score_is_neutral(self) -> None:
        self.assertEqual(rating_color("—"), MISSING_RATING_COLOR)
        self.assertEqual(rating_color(None), MISSING_RATING_COLOR)

    def test_scores_are_clamped_to_supported_range(self) -> None:
        self.assertEqual(rating_color(-1), rating_color(0))
        self.assertEqual(rating_color(11), rating_color(10))


if __name__ == "__main__":
    unittest.main()
