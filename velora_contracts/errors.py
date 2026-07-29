"""Frozen domain error categories from Core Design v1.1."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base typed error safe to cross application-service boundaries."""

    code = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    code = "validation_error"


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class CompatibilityError(DomainError):
    code = "compatibility_error"


class IntegrityError(DomainError):
    code = "integrity_error"


class MigrationError(DomainError):
    code = "migration_error"


class PatchError(DomainError):
    code = "patch_error"


class BackupError(DomainError):
    code = "backup_error"


class RecoverableStorageError(DomainError):
    code = "recoverable_storage_error"


class FatalStorageError(DomainError):
    code = "fatal_storage_error"
