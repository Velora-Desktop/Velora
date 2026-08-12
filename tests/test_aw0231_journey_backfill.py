import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

from app.data.catalog_repository import CATALOG_DB


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "aw0231_journey_backfill.json"
KNOWN_TEMPLATES = {
    "story_campaign", "linear_campaign", "open_world", "rpg",
    "metroidvania", "strategy", "city_builder", "racing",
}


class AW0231JourneyBackfillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_aw0231_journey_backfill.py")],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.entries = cls.payload["entries"]

    def test_manifest_covers_every_active_game_once(self):
        with sqlite3.connect(CATALOG_DB) as db:
            expected = {
                row[0] for row in db.execute(
                    "SELECT catalog_id FROM catalog_items "
                    "WHERE catalog_id LIKE 'g-%' AND is_active=1"
                )
            }
        actual = [entry["game_id"] for entry in self.entries]
        self.assertEqual(expected, set(actual))
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(self.payload["catalog_count"], len(actual))

    def test_assigned_templates_are_registered(self):
        assigned = {
            entry["journey_template_id"] for entry in self.entries
            if entry["journey_template_id"] is not None
        }
        self.assertLessEqual(assigned, KNOWN_TEMPLATES)

    def test_publish_ready_stages_are_ordered_and_stable(self):
        ready = [entry for entry in self.entries if entry["status"] == "publish_ready"]
        self.assertTrue(ready)
        for entry in ready:
            stages = entry["stages"]
            self.assertTrue(stages, entry["game_id"])
            self.assertEqual(
                [stage["order"] for stage in stages], list(range(1, len(stages) + 1))
            )
            self.assertEqual(
                [stage["stage_id"] for stage in stages],
                [f"stage-{number:02d}" for number in range(1, len(stages) + 1)],
            )
            self.assertTrue(all(stage["title"].strip() for stage in stages))

    def test_manual_review_and_not_applicable_do_not_invent_stages(self):
        for entry in self.entries:
            if entry["status"] in {"manual_review", "not_applicable"}:
                self.assertIsNone(entry["journey_template_id"])
                self.assertEqual(entry["stages"], [])

    def test_same_title_releases_remain_distinct(self):
        god_of_war = [entry for entry in self.entries if entry["title"] == "God of War"]
        self.assertEqual({entry["release_year"] for entry in god_of_war}, {2005, 2018})
        self.assertEqual(len({entry["game_id"] for entry in god_of_war}), 2)
        self.assertTrue(all(entry["status"] == "publish_ready" for entry in god_of_war))


if __name__ == "__main__":
    unittest.main()
