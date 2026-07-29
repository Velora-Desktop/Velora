"""Application boundary for official and personal item tags."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.storage.models import UserTag
from app.storage.unit_of_work import CatalogUnitOfWork, UserUnitOfWork
from velora_contracts.enums import SourceType


@dataclass(frozen=True, slots=True)
class ItemTags:
    official: tuple[str, ...]
    personal: tuple[str, ...]


def normalize_tag(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lstrip("#").strip())


class TagService:
    def __init__(self, catalog_db: Path, user_db: Path) -> None:
        self.catalog_db = catalog_db
        self.user_db = user_db

    def get_tags(self, catalog_id: str) -> ItemTags:
        with CatalogUnitOfWork(self.catalog_db) as uow:
            official = tuple(tag.name for tag in uow.catalog.tags_for(catalog_id))
        with UserUnitOfWork(self.user_db) as uow:
            personal = tuple(
                tag.name
                for tag in uow.tags.list_for(SourceType.OFFICIAL, catalog_id)
            )
        return ItemTags(official, personal)

    def save_personal_tags(
        self, catalog_id: str, values: list[str],
    ) -> tuple[str, ...]:
        unique: dict[str, str] = {}
        for value in values:
            normalized = normalize_tag(value)
            if normalized:
                unique.setdefault(normalized.casefold(), normalized)
        records = [
            UserTag(
                f"tag-{uuid.uuid5(uuid.NAMESPACE_URL, 'velora:user-tag:' + key)}",
                name,
            )
            for key, name in unique.items()
        ]
        with UserUnitOfWork(self.user_db) as uow:
            uow.tags.replace_for(SourceType.OFFICIAL, catalog_id, records)
        return tuple(record.name for record in records)
