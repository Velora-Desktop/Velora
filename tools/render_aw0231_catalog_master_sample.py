from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "ui" / "screenshots" / "aw0231_catalog_master_sample.png"
IDS = (
    "g-shooter-fps-002", "g-rpg-action-002", "g-racing-arcade-001", "g-strategy-city-001",
    "g-adventure-aw0092-001", "g-shooter-aw0092-005", "g-shooter-aw0092-010",
    "g-rpg-aw0092-010", "g-rpg-aw0092-016", "g-shooter-tps-002", "g-action-aw0092-002",
    "g-action-aw0092-017", "g-shooter-tps-001", "g-adventure-aw0092-004", "g-adventure-aw0092-005",
    "g-strategy-aw0092-004", "g-shooter-aw0092-011", "g-shooter-aw0092-016",
    "g-rpg-aw0092-008", "g-action-aw0092-003",
)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    root = QWidget()
    root.setStyleSheet("QWidget{background:#071119;color:#f4f7fb} QFrame{background:#0b1720;border:1px solid #263743;border-radius:8px} QLabel{border:none;background:transparent}")
    layout = QGridLayout(root); layout.setContentsMargins(18,18,18,18); layout.setSpacing(12)
    with sqlite3.connect(ROOT / "data" / "catalog.db") as connection:
        connection.row_factory = sqlite3.Row
        for index, game_id in enumerate(IDS):
            row = connection.execute("SELECT * FROM catalog_items WHERE catalog_id=?", (game_id,)).fetchone()
            card = QFrame(); card.setFixedSize(360, 240)
            card_layout = QHBoxLayout(card); card_layout.setContentsMargins(10,10,10,10); card_layout.setSpacing(10)
            cover = QLabel(); cover.setFixedSize(112,168); cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(str(ROOT / row["cover_path"]))
            cover.setPixmap(pixmap.scaled(112,168,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            info = QVBoxLayout(); title = QLabel(row["title"]); title.setWordWrap(True); title.setFont(QFont("Segoe UI",11,QFont.Weight.Bold))
            info.addWidget(title)
            for text in (f"{row['release_year'] or '—'}", f"Разр.: {row['developer'] or '—'}", f"Изд.: {row['publisher'] or '—'}", f"Движок: {row['engine'] or 'review'}", f"Chronology: {'yes' if row['chronology_json'] != '[]' else 'n/a'}"):
                label=QLabel(text); label.setWordWrap(True); info.addWidget(label)
            info.addStretch(); card_layout.addWidget(cover); card_layout.addLayout(info,1)
            layout.addWidget(card,index//4,index%4)
    root.resize(1500, 1280); root.show(); app.processEvents()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True); root.grab().save(str(OUTPUT), "PNG")
    print(OUTPUT)


if __name__ == "__main__":
    main()
