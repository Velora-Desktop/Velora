from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.application.tag_service import TagService, normalize_tag
from app.storage.schema import SchemaManager, utc_now
from app.storage.models import CatalogItem
from app.storage.unit_of_work import CatalogUnitOfWork
from velora_contracts.enums import CatalogLifecycleState, MediaType


class TagServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name)
        self.catalog = root / "catalog.db"
        self.user = root / "user.db"
        manager = SchemaManager()
        manager.create_catalog(self.catalog)
        manager.create_user(self.user, reset_operation_id="tag-test-reset")
        now = utc_now()
        with CatalogUnitOfWork(self.catalog) as uow:
            uow.catalog.add(CatalogItem(
                "game-1", MediaType.GAME, "Doom", "doom", 2020, None, None,
                CatalogLifecycleState.ACTIVE, 1, now, now,
            ))
            uow._session.db.execute(
                "INSERT INTO tags VALUES('official-demons','demons','Демоны',1,1)"
            )
            uow._session.db.execute(
                "INSERT INTO catalog_tags VALUES('game-1','official-demons',0)"
            )
        self.service = TagService(self.catalog, self.user)

    def tearDown(self):
        self.temp.cleanup()

    def test_normalize_and_persist_without_case_duplicates(self):
        saved = self.service.save_personal_tags(
            "game-1", [" #Космос ", "космос", "", "#Демоны"]
        )
        self.assertEqual(saved, ("Космос", "Демоны"))
        reopened = TagService(self.catalog, self.user).get_tags("game-1")
        self.assertEqual(reopened.official, ("Демоны",))
        self.assertEqual(reopened.personal, ("Демоны", "Космос"))

    def test_delete_tag_assignment(self):
        self.service.save_personal_tags("game-1", ["Космос"])
        self.service.save_personal_tags("game-1", [])
        self.assertEqual(self.service.get_tags("game-1").personal, ())

    def test_normalize_optional_hash(self):
        self.assertEqual(normalize_tag("#  Демоны "), "Демоны")


if __name__ == "__main__":
    unittest.main()
