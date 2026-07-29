"""UI-facing presenter for official and personal tags."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.tag_service import TagService


@dataclass(frozen=True, slots=True)
class TagPresentation:
    official: tuple[str, ...]
    personal: tuple[str, ...]


class TagPresenter:
    def __init__(self, service: TagService) -> None:
        self._service = service

    def load(self, catalog_id: str) -> TagPresentation:
        value = self._service.get_tags(catalog_id)
        return TagPresentation(value.official, value.personal)

    def save_personal(
        self, catalog_id: str, values: list[str],
    ) -> TagPresentation:
        self._service.save_personal_tags(catalog_id, values)
        return self.load(catalog_id)
