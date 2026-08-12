"""Render the registered Asset Pack 1 contact sheet for documentation QA."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from PIL import Image, ImageDraw, ImageFont

from app.core.icon_registry import IconRegistry


def render_sheet(assets: list[dict], output: Path, *, scale: float = 1.0) -> None:
    columns, cell_w, cell_h = 5, round(230 * scale), round(150 * scale)
    rows = max(1, (len(assets) + columns - 1) // columns)
    image = QImage(columns * cell_w, rows * cell_h, QImage.Format.Format_ARGB32)
    image.fill(QColor("#071016"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setFont(QFont("Arial", max(8, round(9 * scale))))
    for index, item in enumerate(assets):
        row, column = divmod(index, columns)
        cell = QRect(column * cell_w, row * cell_h, cell_w, cell_h)
        painter.setPen(QColor("#293642"))
        painter.drawRoundedRect(cell.adjusted(6, 6, -6, -6), 8, 8)
        icon_id = item["id"]
        category = icon_id.partition(".")[0]
        icon_size = round(64 * scale)
        pixmap = IconRegistry.pixmap(
            icon_id, icon_size,
            variant=(
                "dark" if item.get("dark_theme_path")
                else "original" if not item.get("tintable") else "auto"
            ),
            category=category,
        )
        if item.get("tintable") and not pixmap.isNull():
            pixmap = IconRegistry.tinted_pixmap(
                icon_id, icon_size, "#EEF1F4", category=category
            )
        x = cell.center().x() - pixmap.width() // 2
        painter.drawPixmap(x, cell.top() + round(24 * scale), pixmap)
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(output)):
        raise RuntimeError(f"Could not save {output}")
    rendered = Image.open(output).convert("RGBA")
    draw = ImageDraw.Draw(rendered)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(str(font_path), max(10, round(13 * scale)))
    for index, item in enumerate(assets):
        row, column = divmod(index, columns)
        label = item["id"]
        box = draw.textbbox((0, 0), label, font=font)
        width = box[2] - box[0]
        draw.text(
            (column * cell_w + (cell_w - width) / 2, row * cell_h + round(108 * scale)),
            label, font=font, fill="#EEF1F4",
        )
    rendered.save(output)


def main() -> int:
    QApplication.instance() or QApplication([])
    manifest = json.loads(
        (ROOT / "assets/icons/asset_pack_1/manifest.json").read_text(encoding="utf-8")
    )
    assets = manifest["assets"]
    output = ROOT / "docs/ui/VELORA_ICON_PACK_AW023_CONTACT_SHEET.png"
    render_sheet(assets, output)
    qa = ROOT / "docs/implementation/qa_aw023_assets"
    for prefix, filename in {
        "genre.": "aw023_assets_genres.png",
        "metadata.": "aw023_assets_metadata.png",
        "service.": "aw023_assets_services.png",
        "brand.": "aw023_assets_brand.png",
    }.items():
        render_sheet([item for item in assets if item["id"].startswith(prefix)], qa / filename)
    render_sheet(assets, qa / "aw023_assets_dark_theme.png")
    for percent in (125, 150, 200):
        render_sheet(assets, qa / f"aw023_assets_dpi_{percent}.png", scale=percent / 100)
    favorite = {"id": "genre.rpg", "tintable": True}
    for state, scale in (("off", 1.0), ("peak", 1.3), ("on", 1.0)):
        render_sheet([favorite], qa / f"aw023_assets_favorite_{state}.png", scale=scale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
