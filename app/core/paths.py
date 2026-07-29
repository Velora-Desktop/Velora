from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Single source of runtime paths for source-run Core Generation 1."""

    root: Path
    project_root: Path = PROJECT_ROOT

    @classmethod
    def source_run(
        cls,
        *,
        root: Path | None = None,
        project_root: Path = PROJECT_ROOT,
    ) -> "AppPaths":
        default_root = (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "Velora"
        )
        return cls(Path(root or default_root).expanduser().resolve(), project_root.resolve())

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def profile(self) -> Path:
        return self.root / "profile"

    @property
    def catalog_db(self) -> Path:
        return self.data / "catalog.db"

    @property
    def user_db(self) -> Path:
        return self.data / "user.db"

    @property
    def legacy_user_db(self) -> Path:
        """Location used by the AW0.1 source-run profile."""
        return self.root / "user.db"

    def active_user_db(self) -> Path:
        """Resolve the durable Schema 1 generation selected by reset."""
        try:
            payload = json.loads(self.active_profile_pointer.read_text(encoding="utf-8"))
            candidate = Path(str(payload["generation_path"])) / "user.db"
            if candidate.is_file():
                return candidate
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return self.user_db

    @property
    def catalog_media(self) -> Path:
        return self.root / "media" / "catalog"

    @property
    def user_media(self) -> Path:
        return self.root / "media" / "user"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def snapshots(self) -> Path:
        return self.backups / "snapshots"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def runtime(self) -> Path:
        return self.root / "runtime"

    @property
    def staging(self) -> Path:
        return self.runtime / "staging"

    @property
    def legacy(self) -> Path:
        return self.root / "legacy"

    @property
    def patch_recovery_journal(self) -> Path:
        return self.runtime / "patch_recovery_state.json"

    @property
    def migration_recovery_journal(self) -> Path:
        return self.runtime / "migration_recovery_state.json"

    @property
    def restore_recovery_journal(self) -> Path:
        return self.runtime / "restore_state.json"

    @property
    def reset_recovery_journal(self) -> Path:
        return self.profile / "reset_state.json"

    @property
    def profile_generations(self) -> Path:
        return self.profile / "generations"

    @property
    def profile_quarantine(self) -> Path:
        return self.profile / "quarantine"

    @property
    def active_profile_pointer(self) -> Path:
        return self.profile / "active_generation.json"

    def ensure_runtime_directories(self) -> None:
        for directory in (
            self.data,
            self.profile,
            self.catalog_media,
            self.user_media,
            self.cache,
            self.backups,
            self.snapshots,
            self.exports,
            self.logs,
            self.runtime,
            self.staging,
            self.legacy,
            self.profile_generations,
            self.profile_quarantine,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def resolve_resource(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return self.project_root / path


DEFAULT_PATHS = AppPaths.source_run()
APP_DATA_DIR = DEFAULT_PATHS.root
BACKUPS_DIR = DEFAULT_PATHS.backups
LOGS_DIR = DEFAULT_PATHS.logs
USER_IMAGES_DIR = DEFAULT_PATHS.user_media


def ensure_runtime_directories() -> None:
    DEFAULT_PATHS.ensure_runtime_directories()


def resolve_resource_path(value: str | Path) -> Path:
    """Resolve catalog resource paths independently from the launch directory."""
    return DEFAULT_PATHS.resolve_resource(value)
