import tempfile
import unittest
from pathlib import Path

from app.data.personal_library_repository import PersonalLibraryRepository
from app.data.user_repository import UserRepository
from app.models.personal_library import ManualList, QueueEntry, ReviewDraft


class Aw009PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=Path(self.temp.name)/"user.db"; UserRepository(self.path); self.repository=PersonalLibraryRepository(self.path)

    def tearDown(self):self.temp.cleanup()

    def test_queue_reordering(self):
        self.repository.save_queue_entry(QueueEntry("a",0,"Пройти следующим",priority="Высокий"));self.repository.save_queue_entry(QueueEntry("b",0))
        self.repository.reorder_queue(["b","a"])
        self.assertEqual(["b","a"],[value.catalog_id for value in self.repository.queue()])

    def test_ranked_manual_list_keeps_previous_position(self):
        value=ManualList(None,"Топ",is_ranked=True); list_id=self.repository.save_manual_list(value);self.repository.add_list_item(list_id,"a");self.repository.add_list_item(list_id,"b");self.repository.reorder_list(list_id,["b","a"])
        rows=self.repository.list_items(list_id);self.assertEqual(("b",1,2),(rows[0]["catalog_id"],rows[0]["position"],rows[0]["previous_position"]))

    def test_draft_journal_archive_and_trash(self):
        self.repository.save_draft(ReviewDraft("a","Обзор","Текст"));self.repository.add_journal_entry("a","Первая глава","3 ч");self.repository.set_archived("a",True)
        value=ManualList(None,"Временный");list_id=self.repository.save_manual_list(value);self.repository.move_list_to_trash(list_id)
        self.assertEqual("Текст",self.repository.draft("a").body);self.assertEqual(1,len(self.repository.journal("a")));self.assertIn("a",self.repository.archived_ids());self.assertEqual(1,len(self.repository.trash()))


if __name__=="__main__":unittest.main()
