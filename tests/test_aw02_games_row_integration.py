from __future__ import annotations

import ast
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.application import (
    GameRowAction, GameRowFilter, GameRowSort, GameRowSortField,
    GamesRowQueryService, LibraryService, PageRequest, PlaythroughService,
    QueryStateKind, RatingService, SortDirection,
)
from app.storage.models import CatalogItem
from app.storage.schema import SchemaManager
from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork
from velora_contracts.enums import (
    CatalogLifecycleState, LibraryMembershipState, MediaType, SourceType,
)
from velora_contracts.ids import CatalogId, OperationId
from velora_contracts.value_objects import CatalogItemRef


class GamesRowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.catalog_db, self.user_db = root / "catalog.db", root / "user.db"
        manager = SchemaManager()
        manager.create_catalog(self.catalog_db)
        manager.create_user(self.user_db, reset_operation_id=self.op())
        self.library = LibraryService(self.catalog_db, self.user_db)
        self.playthroughs = PlaythroughService(self.user_db)
        self.ratings = RatingService(self.user_db)
        self.queries = GamesRowQueryService(self.catalog_db, self.user_db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def op() -> str:
        return str(OperationId.new())

    @staticmethod
    def at(second: int) -> str:
        return f"2026-01-01T00:00:{second:02d}Z"

    def game(self, title: str, second: int) -> CatalogItemRef:
        ref = CatalogItemRef(SourceType.OFFICIAL, str(CatalogId.new()))
        with CatalogUnitOfWork(self.catalog_db) as uow:
            uow.catalog.add(CatalogItem(
                ref.item_id, MediaType.GAME, title, title.casefold(), 2026,
                None, None, CatalogLifecycleState.ACTIVE, 1,
                self.at(second), self.at(second),
            ))
        self.library.add(ref, self.op(), occurred_at=self.at(second))
        return ref

    def playing(self, ref: CatalogItemRef, second: int):
        run = self.playthroughs.create(
            ref, self.op(), initial_status="playing", started_at=self.at(second)
        )
        return run

    def test_01_empty_game_list(self):
        state = self.queries.list_game_rows()
        self.assertEqual(state.kind, QueryStateKind.EMPTY)
        self.assertEqual(state.page.total_items, 0)

    def test_02_single_row(self):
        ref = self.game("One", 1)
        state = self.queries.list_game_rows()
        self.assertEqual(state.kind, QueryStateKind.RESULT)
        self.assertEqual(state.rows[0].selection.item_id, ref.item_id)

    def test_03_multiple_rows(self):
        for index, title in enumerate(("One", "Two", "Three"), 1):
            self.game(title, index)
        self.assertEqual(self.queries.list_game_rows().page.total_items, 3)

    def test_04_stable_ordering(self):
        for title in ("Same", "Same", "Same"):
            self.game(title, 1)
        first = [r.selection.stable_key for r in self.queries.list_game_rows().rows]
        second = [r.selection.stable_key for r in self.queries.list_game_rows().rows]
        self.assertEqual(first, second)

    def test_05_sort_by_title(self):
        for index, title in enumerate(("Zulu", "Alpha", "Middle"), 1):
            self.game(title, index)
        state = self.queries.list_game_rows(sort=GameRowSort(
            GameRowSortField.TITLE, SortDirection.ASCENDING
        ))
        self.assertEqual([r.title for r in state.rows], ["Alpha", "Middle", "Zulu"])

    def test_06_sort_by_updated_at(self):
        self.game("First", 1)
        self.game("Last", 2)
        state = self.queries.list_game_rows(sort=GameRowSort(
            GameRowSortField.UPDATED_AT, SortDirection.DESCENDING
        ))
        self.assertEqual([r.title for r in state.rows], ["Last", "First"])

    def test_07_sort_by_rating(self):
        low, high = self.game("Low", 1), self.game("High", 2)
        self.ratings.save_final(low, 40, {}, self.op(), occurred_at=self.at(3))
        self.ratings.save_final(high, 90, {}, self.op(), occurred_at=self.at(4))
        state = self.queries.list_game_rows(sort=GameRowSort(
            GameRowSortField.PERSONAL_RATING, SortDirection.DESCENDING
        ))
        self.assertEqual([r.title for r in state.rows], ["High", "Low"])

    def test_08_sort_by_playtime(self):
        short, long = self.game("Short", 1), self.game("Long", 2)
        one, two = self.playing(short, 3), self.playing(long, 4)
        self.playthroughs.add_playtime(one.playthrough_id, 10, self.op())
        self.playthroughs.add_playtime(two.playthrough_id, 100, self.op())
        state = self.queries.list_game_rows(sort=GameRowSort(
            GameRowSortField.TOTAL_PLAYTIME, SortDirection.DESCENDING
        ))
        self.assertEqual([r.title for r in state.rows], ["Long", "Short"])

    def test_09_filter_by_lifecycle(self):
        active, archived = self.game("Active", 1), self.game("Archived", 2)
        with UserUnitOfWork(self.user_db) as uow:
            state = uow.library.get(archived.source_type, archived.item_id)
            uow.library.upsert(replace(
                state, membership_state=LibraryMembershipState.ARCHIVED,
                archived_at=self.at(3),
            ))
        result = self.queries.list_game_rows(filters=GameRowFilter(
            lifecycle_state=LibraryMembershipState.ARCHIVED
        ))
        self.assertEqual([r.title for r in result.rows], ["Archived"])

    def test_10_filter_by_playthrough_status(self):
        playing, other = self.game("Playing", 1), self.game("Other", 2)
        self.playing(playing, 3)
        result = self.queries.list_game_rows(filters=GameRowFilter(
            playthrough_status="playing"
        ))
        self.assertEqual([r.title for r in result.rows], ["Playing"])

    def test_11_pagination_first_page(self):
        for index in range(5):
            self.game(f"Game {index}", index + 1)
        result = self.queries.list_game_rows(
            sort=GameRowSort(GameRowSortField.TITLE, SortDirection.ASCENDING),
            pagination=PageRequest(1, 2),
        )
        self.assertEqual(len(result.rows), 2)
        self.assertEqual(result.page.total_pages, 3)

    def test_12_pagination_last_page(self):
        for index in range(5):
            self.game(f"Game {index}", index + 1)
        result = self.queries.list_game_rows(pagination=PageRequest(3, 2))
        self.assertEqual(len(result.rows), 1)

    def test_13_no_duplicates_between_pages(self):
        for index in range(5):
            self.game(f"Game {index}", index + 1)
        pages = [
            self.queries.list_game_rows(pagination=PageRequest(page, 2)).rows
            for page in (1, 2, 3)
        ]
        ids = [row.selection.stable_key for page in pages for row in page]
        self.assertEqual(len(ids), len(set(ids)))

    def test_14_get_single_row(self):
        ref = self.game("Single", 1)
        state = self.queries.get_game_row(ref)
        self.assertEqual(state.kind, QueryStateKind.RESULT)
        self.assertEqual(state.row.title, "Single")

    def test_15_refresh_single_row(self):
        ref = self.game("Refresh", 1)
        before = self.queries.get_game_row(ref).row
        run = self.playing(ref, 2)
        after = self.queries.refresh_game_row(ref).row
        self.assertIsNone(before.playthrough_status)
        self.assertEqual(after.playthrough_status, "playing")

    def test_16_row_actions_for_unstarted_game(self):
        row = self.queries.get_game_row(self.game("New", 1)).row
        self.assertEqual(
            self.queries.resolve_row_actions(row),
            (GameRowAction.OPEN, GameRowAction.START_PLAYTHROUGH),
        )

    def test_17_row_actions_for_playing_game(self):
        ref = self.game("Playing", 1)
        self.playing(ref, 2)
        actions = self.queries.resolve_row_actions(
            self.queries.get_game_row(ref).row
        )
        self.assertIn(GameRowAction.CONTINUE_PLAYTHROUGH, actions)
        self.assertIn(GameRowAction.COMPLETE_PLAYTHROUGH, actions)
        self.assertNotIn(GameRowAction.START_PLAYTHROUGH, actions)

    def test_18_row_actions_for_completed_game(self):
        ref = self.game("Completed", 1)
        run = self.playing(ref, 2)
        self.playthroughs.set_status(run.playthrough_id, "completed", self.op())
        actions = self.queries.resolve_row_actions(
            self.queries.get_game_row(ref).row
        )
        self.assertEqual(actions, (
            GameRowAction.OPEN, GameRowAction.START_PLAYTHROUGH,
            GameRowAction.ADD_IMPRESSION, GameRowAction.RATE,
        ))

    def test_19_typed_error_state(self):
        missing = CatalogItemRef(SourceType.OFFICIAL, str(CatalogId.new()))
        state = self.queries.get_row_state(missing)
        self.assertEqual(state.kind, QueryStateKind.ERROR)
        self.assertEqual(state.error.code, "not_found")

    def test_20_no_ui_or_pyside_dependencies(self):
        root = Path(__file__).parents[1] / "app" / "application"
        for path in (
            root / "game_row_contracts.py", root / "game_row_queries.py"
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            self.assertFalse(any(
                name.startswith(("PySide6", "app.ui")) for name in imports
            ))


if __name__ == "__main__":
    unittest.main()
