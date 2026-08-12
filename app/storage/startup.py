"""AW0.2 source-run storage bootstrap and one-time reset coordination."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from velora_contracts.enums import (
    CatalogLifecycleState, MediaType, SourceType,
)
from velora_contracts.ids import OperationId
from velora_contracts.value_objects import CatalogItemRef

from app.core.paths import AppPaths

from .models import CatalogItem, Tag
from .recovery import AtomicJsonJournal
from .reset import AW02ResetManager, ResetHardStop
from .schema import SchemaManager, utc_now
from .unit_of_work import CatalogUnitOfWork, UserUnitOfWork


DOOM_ETERNAL_ID = "9df7cc01-d487-4cd7-814d-e70ec7967a4a"


@dataclass(frozen=True, slots=True)
class StartupStorage:
    catalog_db: Path
    user_db: Path
    reset_performed: bool
    snapshot_root: Path
    legacy_root: Path


def prepare_aw02_storage(paths: AppPaths | None = None) -> StartupStorage:
    """Return valid Schema 1 paths; never mutates a legacy DB before snapshot."""
    selected = paths or AppPaths.source_run()
    selected.ensure_runtime_directories()
    schema = SchemaManager()
    reset_performed = False

    active_user = selected.active_user_db()
    if not _valid_schema(schema, active_user):
        if selected.legacy_user_db.is_file() or selected.user_db.is_file():
            result = AW02ResetManager(selected, schema=schema).start_or_resume()
            active_user = result.generation_path / "user.db"
            reset_performed = True
        else:
            operation_id = str(uuid4())
            generation = selected.profile_generations / operation_id
            generation.mkdir(parents=True, exist_ok=False)
            active_user = generation / "user.db"
            schema.create_user(active_user, reset_operation_id=operation_id)
            AtomicJsonJournal(selected.active_profile_pointer).write({
                "operation_id": operation_id,
                "generation_path": str(generation),
                "core_generation": 1,
            })

    if not _valid_schema(schema, selected.catalog_db):
        if selected.catalog_db.exists():
            raise ResetHardStop("Runtime catalog.db exists but is not Schema 1")
        schema.create_catalog(selected.catalog_db)
    _ensure_doom_catalog_item(selected.catalog_db)
    schema.ensure_aw023_user_extensions(active_user)
    _ensure_doom_library_item(selected.catalog_db, active_user)
    schema.validate(selected.catalog_db)
    schema.validate(active_user)
    return StartupStorage(
        selected.catalog_db, active_user, reset_performed,
        selected.snapshots, selected.legacy,
    )


def _valid_schema(schema: SchemaManager, path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        schema.validate(path)
        return True
    except Exception:
        return False


def _ensure_doom_catalog_item(database: Path) -> None:
    with CatalogUnitOfWork(database) as uow:
        if uow.catalog.get(DOOM_ETERNAL_ID) is None:
            now = utc_now()
            uow.catalog.add(CatalogItem(
                DOOM_ETERNAL_ID,
                MediaType.GAME,
                "Doom Eternal",
                "doom eternal",
                2020,
                "Динамичный шутер от первого лица от id Software.",
                "Doom Eternal — продолжение серии DOOM и тестовая вертикаль AW0.2.",
                CatalogLifecycleState.ACTIVE,
                1,
                now,
                now,
            ))
        for order, name in enumerate((
            "от первого лица", "стрельба", "динамичный бой",
            "космос", "демоны", "одиночная игра",
        )):
            tag_id = f"doom-tag-{order + 1}"
            uow.catalog.ensure_tag(Tag(tag_id, name))
            uow.catalog.assign_tag(DOOM_ETERNAL_ID, tag_id, order)


def _ensure_doom_library_item(catalog_db: Path, user_db: Path) -> None:
    """Make the approved slice visible through an atomic service mutation."""
    with UserUnitOfWork(user_db) as uow:
        if uow.library.get(SourceType.OFFICIAL, DOOM_ETERNAL_ID) is not None:
            return
    # Local import keeps the bootstrap free from a module import cycle.
    from app.application.game_services import LibraryService

    LibraryService(catalog_db, user_db).add(
        CatalogItemRef(SourceType.OFFICIAL, DOOM_ETERNAL_ID),
        OperationId.new(),
    )
