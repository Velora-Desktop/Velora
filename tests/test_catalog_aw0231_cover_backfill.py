from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "data" / "catalog.db"
MANIFEST = ROOT / "assets" / "covers" / "catalog" / "aw0231_cover_sources.json"


def test_every_game_has_a_valid_local_aw0231_cover() -> None:
    connection = sqlite3.connect(CATALOG_DB)
    rows = connection.execute(
        "SELECT catalog_id, title, cover_path FROM catalog_items "
        "WHERE catalog_id LIKE 'g-%' ORDER BY catalog_id"
    ).fetchall()
    connection.close()

    assert len(rows) == 101
    for catalog_id, title, cover_path in rows:
        assert cover_path, f"{catalog_id} ({title}) has no cover_path"
        normalized = cover_path.replace("\\", "/").casefold()
        assert normalized.startswith("assets/covers/catalog/")
        assert "placeholder" not in normalized
        path = ROOT / cover_path
        assert path.is_file(), f"missing cover file for {catalog_id}: {cover_path}"
        image = QImage(str(path))
        assert not image.isNull(), f"broken cover for {catalog_id}: {cover_path}"
        assert (image.width(), image.height()) == (300, 450)


def test_aw0231_source_manifest_matches_backfilled_files() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["patch"] == "AW0.301"
    assert payload["format"] == "JPEG"
    assert payload["stored_size"] == {"width": 300, "height": 450}
    assert len(payload["entries"]) == 91

    catalog_ids: set[str] = set()
    for entry in payload["entries"]:
        catalog_id = entry["catalog_id"]
        assert catalog_id not in catalog_ids
        catalog_ids.add(catalog_id)
        path = ROOT / entry["local_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        assert entry["source_height"] > entry["source_width"]


def test_aw0231_catalog_integrity_and_foreign_keys() -> None:
    connection = sqlite3.connect(CATALOG_DB)
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    connection.close()
