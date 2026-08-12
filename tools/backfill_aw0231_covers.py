"""One-shot AW0.231 catalog cover backfill.

Downloads a reviewed set of official store posters or exact-edition box art,
normalizes every image to Velora's established 300x450 JPEG format, validates
the result, and updates catalog.db in one explicit transaction.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "catalog.db"
COVER_DIR = ROOT / "assets" / "covers" / "catalog"
MANIFEST_PATH = COVER_DIR / "aw0231_cover_sources.json"
TARGET_SIZE = (300, 450)


def steam(app_id: int) -> str:
    return (
        "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"
        f"{app_id}/library_600x900_2x.jpg"
    )


# catalog_id: (source URL, source label). Every non-Steam entry was reviewed
# against the title/edition represented by the catalog row.
SOURCES: dict[str, tuple[str, str]] = {
    "g-adventure-aw0092-016": (steam(1222700), "Steam official store art"),
    "g-strategy-rts-001": (steam(813780), "Steam official store art"),
    "g-action-aw0092-016": ("https://upload.wikimedia.org/wikipedia/en/e/ed/Alan_Wake_2_box_art.jpg", "Exact-edition box art"),
    "g-strategy-aw0092-012": (steam(916440), "Steam official store art"),
    "g-action-aw0092-013": ("https://upload.wikimedia.org/wikipedia/en/7/77/Assassins_Creed_2_Box_Art.JPG", "Exact-edition box art"),
    "g-action-aw0092-014": (steam(242050), "Steam official store art"),
    "g-rpg-classic-001": (steam(1086940), "Steam official store art"),
    "g-adventure-aw0092-006": (steam(504230), "Steam official store art"),
    "g-strategy-city-001": (steam(255710), "Steam official store art"),
    "g-strategy-aw0092-011": (steam(1213210), "Steam official store art"),
    "g-strategy-aw0092-010": (steam(231430), "Steam official store art"),
    "g-strategy-aw0092-004": (steam(1158310), "Steam official store art"),
    "g-adventure-aw0092-010": (steam(268910), "Steam official store art"),
    "g-rpg-aw0092-001": (steam(1091500), "Steam official store art"),
    "g-rpg-aw0092-004": (steam(374320), "Steam official store art"),
    "g-adventure-aw0092-007": (steam(588650), "Steam official store art"),
    "g-action-aw0092-010": ("https://upload.wikimedia.org/wikipedia/en/2/22/Death_Stranding.jpg", "Exact-edition box art"),
    "g-shooter-aw0092-014": (steam(1252330), "Steam official store art"),
    "g-rpg-aw0092-016": (steam(2344520), "Steam official store art"),
    "g-rpg-aw0092-008": ("https://upload.wikimedia.org/wikipedia/en/0/0d/Disco_Elysium_Poster.jpeg", "Exact-edition box art"),
    "g-shooter-aw0092-011": (steam(205100), "Steam official store art"),
    "g-shooter-aw0092-012": (steam(403640), "Steam official store art"),
    "g-rpg-aw0092-007": (steam(435150), "Steam official store art"),
    "g-rpg-aw0092-006": ("https://upload.wikimedia.org/wikipedia/en/8/89/Dragon_Age_Origins_cover.png", "Exact-edition box art"),
    "g-rpg-action-002": (steam(1245620), "Steam official store art"),
    "g-strategy-aw0092-005": (steam(236850), "Steam official store art"),
    "g-strategy-aw0092-007": (steam(427520), "Steam official store art"),
    "g-rpg-aw0092-003": (steam(377160), "Steam official store art"),
    "g-shooter-aw0092-007": (steam(220240), "Steam official store art"),
    "g-shooter-aw0092-008": (steam(552520), "Steam official store art"),
    "g-shooter-aw0092-009": (steam(2369390), "Steam official store art"),
    "g-rpg-aw0092-010": ("https://upload.wikimedia.org/wikipedia/en/c/ce/FFVIIRemake.png", "Exact-edition box art"),
    "g-racing-arcade-001": (steam(1551360), "Steam official store art"),
    "g-strategy-aw0092-009": (steam(323190), "Steam official store art"),
    "g-action-aw0092-004": ("https://upload.wikimedia.org/wikipedia/en/b/b6/Ghost_of_Tsushima.jpg", "Exact-edition box art"),
    "g-action-aw0092-002": (steam(1593500), "Steam official store art"),
    "g-action-aw0092-003": (steam(2322010), "Steam official store art"),
    "g-racing-sim-001": ("https://upload.wikimedia.org/wikipedia/en/1/14/Gran_Turismo_7_cover_art.jpg", "Exact-edition box art"),
    "g-action-aw0092-001": ("https://upload.wikimedia.org/wikipedia/en/a/a5/Grand_Theft_Auto_V.png", "Exact-edition box art"),
    "g-adventure-aw0092-004": (steam(1145360), "Steam official store art"),
    "g-strategy-aw0092-013": (steam(394360), "Steam official store art"),
    "g-action-aw0092-012": ("https://upload.wikimedia.org/wikipedia/en/4/4b/Hitman_3_Packart.jpg", "Exact-edition box art"),
    "g-adventure-aw0092-005": (steam(367520), "Steam official store art"),
    "g-rpg-aw0092-015": ("https://upload.wikimedia.org/wikipedia/en/6/69/Horizon_Forbidden_West_cover_art.jpg", "Exact-edition box art"),
    "g-rpg-aw0092-014": ("https://upload.wikimedia.org/wikipedia/en/3/3e/Horizon_Zero_Dawn_cover_art.jpg", "Exact-edition box art"),
    "g-strategy-aw0092-015": (steam(590380), "Steam official store art"),
    "g-adventure-aw0092-015": (steam(1426210), "Steam official store art"),
    "g-rpg-aw0092-011": (steam(379430), "Steam official store art"),
    "g-action-aw0092-005": ("https://upload.wikimedia.org/wikipedia/en/e/e1/Spider-Man_PS4_cover.jpg", "Exact-edition box art"),
    "g-action-aw0092-006": (steam(1817190), "Steam official store art"),
    "g-rpg-aw0092-005": (steam(1328670), "Steam official store art"),
    "g-shooter-tps-001": (steam(204100), "Steam official store art"),
    "g-action-aw0092-011": (steam(287700), "Steam official store art"),
    "g-shooter-aw0092-006": (steam(412020), "Steam official store art"),
    "g-adventure-aw0092-001": ("https://store-images.s-microsoft.com/image/apps.53095.13850085746326678.06e2dc5c-7997-46e9-a8e6-0e48b57cb13b.419e3c9d-9dd3-4a28-a9f3-a12350215871", "Microsoft/Xbox official poster"),
    "g-rpg-aw0092-012": (steam(582010), "Steam official store art"),
    "g-racing-arcade-002": ("https://upload.wikimedia.org/wikipedia/en/8/8e/Need_for_Speed_Most_Wanted_Box_Art.jpg", "Exact 2005-edition box art"),
    "g-rpg-aw0092-013": (steam(524220), "Steam official store art"),
    "g-adventure-aw0092-013": (steam(275850), "Steam official store art"),
    "g-strategy-aw0092-016": (steam(466560), "Steam official store art"),
    "g-adventure-aw0092-008": (steam(261570), "Steam official store art"),
    "g-adventure-aw0092-009": (steam(1057090), "Steam official store art"),
    "g-adventure-aw0092-011": (steam(753640), "Steam official store art"),
    "g-shooter-aw0092-004": (steam(2357570), "Steam official store art"),
    "g-rpg-aw0092-009": (steam(1687950), "Steam official store art"),
    "g-shooter-aw0092-010": (steam(480490), "Steam official store art"),
    "g-adventure-action-001": (steam(1174180), "Steam official store art"),
    "g-shooter-tps-002": ("https://upload.wikimedia.org/wikipedia/en/d/d9/Resi4-gc-cover.jpg", "Exact original 2005-edition box art"),
    "g-strategy-aw0092-008": (steam(294100), "Steam official store art"),
    "g-shooter-aw0092-016": (steam(1643320), "Steam official store art"),
    "g-adventure-aw0092-014": (steam(1172620), "Steam official store art"),
    "g-action-aw0092-015": (steam(814380), "Steam official store art"),
    "g-strategy-turn-001": (steam(289070), "Steam official store art"),
    "g-strategy-aw0092-002": ("https://upload.wikimedia.org/wikipedia/en/2/20/StarCraft_II_-_Box_Art.jpg", "Exact Wings of Liberty box art"),
    "g-adventure-aw0092-003": (steam(413150), "Steam official store art"),
    "g-strategy-aw0092-006": (steam(281990), "Steam official store art"),
    "g-adventure-aw0092-012": (steam(264710), "Steam official store art"),
    "g-adventure-aw0092-002": (steam(105600), "Steam official store art"),
    "g-rpg-aw0092-002": (steam(72850), "Steam official store art for original edition"),
    "g-action-aw0092-008": (steam(1888930), "Steam official store art"),
    "g-action-aw0092-009": ("https://upload.wikimedia.org/wikipedia/en/4/4f/TLOU_P2_Box_Art_2.png", "Exact original-edition box art"),
    "g-rpg-action-001": (steam(292030), "Steam official store art"),
    "g-shooter-fps-006": (steam(1237970), "Steam official store art"),
    "g-shooter-aw0092-005": (steam(359550), "Steam official store art"),
    "g-strategy-aw0092-003": (steam(1142710), "Steam official store art"),
    "g-action-aw0092-007": ("https://upload.wikimedia.org/wikipedia/en/1/1a/Uncharted_4_box_artwork.jpg", "Exact-edition box art"),
    "g-shooter-aw0092-002": ("https://store-images.s-microsoft.com/image/apps.44472.13663857844271189.86bf8848-7dfd-487b-bd91-d633447aeada.bcc2ad6e-75f4-4075-a5ed-9af6975b27ec", "Microsoft/Xbox official PC poster"),
    "g-strategy-aw0092-014": ("https://upload.wikimedia.org/wikipedia/en/6/66/WarcraftIII.jpg", "Exact Reign of Chaos box art"),
    "g-shooter-aw0092-015": (steam(201810), "Steam official store art"),
    "g-strategy-aw0092-001": (steam(268500), "Steam official store art"),
}


def slugify(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")
    return value or hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Velora-AW0.231-CoverBackfill/1.0"},
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
            time.sleep(0.2)
            return payload
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable download retry state")


def normalize(raw: bytes, target: Path) -> tuple[int, int]:
    image = QImage.fromData(raw)
    if image.isNull():
        raise ValueError("downloaded resource is not a readable raster image")
    source_size = (image.width(), image.height())
    if image.height() <= image.width():
        raise ValueError(f"resource is not portrait: {source_size}")
    scaled = image.scaled(
        *TARGET_SIZE,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - TARGET_SIZE[0]) // 2)
    y = max(0, (scaled.height() - TARGET_SIZE[1]) // 2)
    final = scaled.copy(x, y, *TARGET_SIZE).convertToFormat(QImage.Format.Format_RGB888)
    if final.size().toTuple() != TARGET_SIZE or not final.save(str(target), "JPG", 92):
        raise ValueError("failed to save normalized JPEG")
    return source_size


def main() -> int:
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT catalog_id, title, cover_path FROM catalog_items "
        "WHERE catalog_id LIKE 'g-%' ORDER BY title"
    ).fetchall()
    missing = [r for r in rows if not (r["cover_path"] or "").strip()]
    unknown = sorted(r["catalog_id"] for r in missing if r["catalog_id"] not in SOURCES)
    if unknown:
        raise RuntimeError(f"unreviewed missing games: {unknown}")

    manifest: list[dict[str, object]] = []
    downloaded: list[tuple[str, str]] = []
    try:
        for index, row in enumerate(missing, 1):
            catalog_id, title = row["catalog_id"], row["title"]
            url, source_kind = SOURCES[catalog_id]
            target = COVER_DIR / f"{slugify(title)}.jpg"
            print(f"[{index:02d}/{len(missing)}] {title}")
            raw = download(url)
            source_width, source_height = normalize(raw, target)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            relative = target.relative_to(ROOT).as_posix()
            downloaded.append((catalog_id, relative))
            manifest.append(
                {
                    "catalog_id": catalog_id,
                    "title": title,
                    "local_path": relative,
                    "source_url": url,
                    "source_kind": source_kind,
                    "source_width": source_width,
                    "source_height": source_height,
                    "stored_width": TARGET_SIZE[0],
                    "stored_height": TARGET_SIZE[1],
                    "sha256": digest,
                }
            )
    except Exception:
        for _, relative in downloaded:
            (ROOT / relative).unlink(missing_ok=True)
        raise

    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany(
            "UPDATE catalog_items SET cover_path = ? WHERE catalog_id = ?",
            [(path, catalog_id) for catalog_id, path in downloaded],
        )
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("catalog integrity check failed")
        connection.commit()
    except Exception:
        connection.rollback()
        for _, relative in downloaded:
            (ROOT / relative).unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "patch": "AW0.231",
                "format": "JPEG",
                "stored_size": {"width": 300, "height": 450},
                "entries": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Updated {len(downloaded)} catalog covers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
