"""Synchronous, best-effort post-commit notification dispatcher."""

from __future__ import annotations

import logging
from collections.abc import Callable

from velora_contracts.events import DomainEvent

_LOG = logging.getLogger(__name__)


class InProcessEventDispatcher:
    def __init__(self) -> None:
        self._handlers: list[Callable[[DomainEvent], None]] = []

    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in tuple(self._handlers):
            try:
                handler(event)
            except Exception:
                _LOG.exception("Post-commit event handler failed: %s", event.event_name)
