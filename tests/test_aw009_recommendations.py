from types import SimpleNamespace
import unittest

from app.models.personal_library import QueueEntry
from app.services.library_recommendation_service import LibraryRecommendationService


class Aw009RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            SimpleNamespace(catalog_id="g-1", title="Alan Wake 2", media_type="games", duration_minutes=240, user_interacted=False, personal_score="—", category="Хоррор", status="НЕ НАЧИНАЛ"),
            SimpleNamespace(catalog_id="m-1", title="Interstellar", media_type="movies", duration_minutes=180, user_interacted=False, personal_score="—", category="Фантастика", status="НЕ СМОТРЕЛ"),
        ]
        self.queue = [
            QueueEntry("g-1", 1, "Пройти следующим", "", "Высокий", "Связано с целью"),
            QueueEntry("m-1", 2, "На выходных", "", "Обычный", ""),
        ]

    def test_recommendation_is_local_and_explainable(self):
        result, reasons = LibraryRecommendationService.recommend(self.items, self.queue, media_type="games")
        self.assertEqual(result.catalog_id, "g-1")
        self.assertTrue(reasons)

    def test_queue_duration_requires_complete_data(self):
        self.assertEqual(LibraryRecommendationService.queue_duration(self.items, self.queue), (2, 420))
        self.items[1].duration_minutes = 0
        self.assertEqual(LibraryRecommendationService.queue_duration(self.items, self.queue), (2, None))


if __name__ == "__main__":
    unittest.main()
