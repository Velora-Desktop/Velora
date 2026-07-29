"""Thin Qt controller for Doom; persistence stays in the application layer."""
from app.application.doom_vertical_slice import DoomVerticalSlice
from app.application.game_row_contracts import GameRowAction
from app.core.runtime import startup_storage
from app.ui.catalog.single_row_integration import TARGET_LEGACY_GAME_ID
from app.ui.game_detail.doom_aw02_panel import (
    request_checkpoint, request_impression, request_personal_rating,
    request_playtime,
)
from PySide6.QtWidgets import QMessageBox


class DoomIntegrationController:
    def __init__(self, catalog_view) -> None:
        storage = startup_storage()
        if storage is None:
            raise RuntimeError("AW0.2 storage was not prepared by the entry point")
        self.slice = DoomVerticalSlice(storage.catalog_db, storage.user_db)
        self.catalog_view = catalog_view

    @classmethod
    def create(cls, catalog_view):
        return cls(catalog_view) if startup_storage() is not None else None

    @staticmethod
    def handles(game) -> bool:
        return getattr(game, "catalog_id", "") == TARGET_LEGACY_GAME_ID

    def status_changed(self, game, status: str) -> None:
        if self.handles(game):
            self.slice.set_status(status)
            self.catalog_view.refresh_integrated_row(game.catalog_id)

    def playtime_changed(self, game, total_hours: float) -> None:
        if self.handles(game):
            self.slice.set_total_playtime_hours(total_hours)
            self.catalog_view.refresh_integrated_row(game.catalog_id)

    def rating_changed(self, game, _score: str) -> None:
        if self.handles(game):
            self.slice.save_final_rating(dict(game.rating_criteria))
            self.catalog_view.refresh_integrated_row(game.catalog_id)

    def handle_row_action(self, game, action_name: str) -> None:
        if not self.handles(game):
            return
        action = GameRowAction(action_name)
        parent = self.catalog_view.window()
        try:
            if action in (
                GameRowAction.START_PLAYTHROUGH,
                GameRowAction.CONTINUE_PLAYTHROUGH,
            ):
                self.slice.set_status("ПРОХОЖУ")
            elif action is GameRowAction.ADD_PLAYTIME:
                value = request_playtime(parent)
                if value:
                    self.slice.add_playtime(*value)
            elif action is GameRowAction.ADD_CHECKPOINT:
                value = request_checkpoint(parent)
                if value:
                    self.slice.save_checkpoint(**value)
            elif action is GameRowAction.ADD_IMPRESSION:
                value = request_impression(parent)
                if value:
                    self.slice.add_impression(*value)
            elif action is GameRowAction.RATE:
                value = request_personal_rating(parent)
                if value:
                    self.slice.save_personal_rating(*value)
            elif action is GameRowAction.COMPLETE_PLAYTHROUGH:
                self.slice.set_status("ПРОШЁЛ")
        except Exception as exc:
            QMessageBox.warning(parent, "Doom Eternal · AW0.2", str(exc))
        finally:
            self.catalog_view.refresh_integrated_row(game.catalog_id)
            detail = getattr(parent, "game_detail", None)
            if detail is not None:
                detail.refresh_aw02()
