from __future__ import annotations

import os
from pathlib import Path


APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Velora"
BACKUPS_DIR = APP_DATA_DIR / "backups"
LOGS_DIR = APP_DATA_DIR / "logs"
USER_IMAGES_DIR = APP_DATA_DIR / "images"


def ensure_runtime_directories() -> None:
    for directory in (APP_DATA_DIR, BACKUPS_DIR, LOGS_DIR, USER_IMAGES_DIR):
        directory.mkdir(parents=True, exist_ok=True)
