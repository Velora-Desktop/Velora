"""Build the reviewed AW0.231 official Journey publication manifest.

The manifest is catalog-only input for Studio's generic publish bridge.  This
tool deliberately never opens user.db and never invents stages for uncertain
or non-linear games.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.catalog_repository import CATALOG_DB

OUTPUT = ROOT / "data" / "aw0231_journey_backfill.json"


def _chapters(count: int) -> tuple[str, ...]:
    return tuple(f"Chapter {number}" for number in range(1, count + 1))


# Only structures with stable, verifiable chapter/mission boundaries belong
# here.  Keying by catalog_id prevents same-title releases from colliding.
CURATED: dict[str, tuple[str, tuple[str, ...]]] = {
    "g-shooter-fps-002": ("story_campaign", (
        "Ад на Земле", "Ликование", "База сектантов", "База DOOM-охотников",
        "Кровавое супергнездо", "Комплекс Комитета", "Марс Ядро", "Сентинел Прайм",
        "Тарас Набад", "Некравол", "Некравол — часть II", "Урдак", "Последний грех",
    )),
    "g-shooter-aw0092-011": ("linear_campaign", (
        "Dishonored", "High Overseer Campbell", "House of Pleasure",
        "The Royal Physician", "Lady Boyle's Last Party", "Return to the Tower",
        "The Flooded District", "The Loyalists", "The Light at the End",
    )),
    "g-shooter-fps-003": ("linear_campaign", (
        "Point Insertion", "A Red Letter Day", "Route Kanal", "Water Hazard",
        "Black Mesa East", "We Don't Go to Ravenholm", "Highway 17",
        "Sandtraps", "Nova Prospekt", "Entanglement", "Anticitizen One",
        "Follow Freeman!", "Our Benefactors", "Dark Energy",
    )),
    "g-shooter-fps-006": ("story_campaign", (
        "The Pilot's Gauntlet", "BT-7274", "Blood and Rust", "Into the Abyss",
        "Effect and Cause", "The Beacon", "Trial by Fire", "The Ark",
        "The Fold Weapon",
    )),
    "g-shooter-fps-007": ("linear_campaign", (
        "Welcome to Rapture", "Medical Pavilion", "Neptune's Bounty",
        "Smuggler's Hideout", "Arcadia", "Farmer's Market", "Fort Frolic",
        "Hephaestus", "Rapture Central Control", "Olympus Heights",
        "Apollo Square", "Point Prometheus", "Proving Grounds", "Fontaine",
    )),
    "g-shooter-aw0092-013": ("linear_campaign", (
        "The Lighthouse", "Welcome Center", "Raffle Square", "Comstock Center",
        "Monument Island", "Battleship Bay", "Soldier's Field", "Hall of Heroes",
        "Finkton Docks", "The Factory", "Emporia", "Comstock House",
        "Hand of the Prophet", "Sea of Doors",
    )),
    "g-shooter-tps-002": ("linear_campaign", _chapters(16)),
    "g-adventure-aw0092-006": ("linear_campaign", (
        "Forsaken City", "Old Site", "Celestial Resort", "Golden Ridge",
        "Mirror Temple", "Reflection", "The Summit", "Epilogue", "Core", "Farewell",
    )),
    "g-adventure-aw0092-010": ("linear_campaign", (
        "Inkwell Isle One", "Inkwell Isle Two", "Inkwell Isle Three", "Inkwell Hell",
    )),
    "g-action-aw0092-008": ("linear_campaign", (
        "Hometown", "The Quarantine Zone", "The Outskirts", "Bill's Town",
        "Pittsburgh", "The Suburbs", "Tommy's Dam", "The University",
        "Lakeside Resort", "Bus Depot", "The Firefly Lab", "Jackson",
    )),
    "g-action-aw0092-009": ("story_campaign", (
        "Jackson", "Seattle Day 1", "Seattle Day 2", "Seattle Day 3", "The Park",
        "Seattle Day 1 - Abby", "Seattle Day 2 - Abby", "Seattle Day 3 - Abby",
        "The Farm", "Santa Barbara", "The Farm - Epilogue",
    )),
    "g-action-aw0092-002": ("story_campaign", (
        "The Aegean Sea", "The Gates of Athens", "The Road to Athens",
        "Athens Town Square", "Rooftops of Athens", "Temple of the Oracle",
        "The Sewers of Athens", "Desert of Lost Souls", "Pandora's Temple",
        "The Cliffs of Madness", "The Architect's Tomb", "The Path of Hades",
    )),
    "g-action-aw0092-017": ("open_world", (
        "The Marked Trees", "Path to the Mountain", "A Realm Beyond",
        "The Light of Alfheim", "Inside the Mountain", "A New Destination",
        "The Magic Chisel", "Behind the Lock", "The Sickness", "The Black Rune",
        "Return to the Summit", "Escape from Helheim", "A Path to Jotunheim",
        "Between the Realms", "Jotunheim in Reach", "Mother's Ashes",
    )),
}


# No official ordered stage list is published for these structures.  A proper
# template is still assigned, but no fake stages are generated.
TEMPLATE_BY_ID: dict[str, str] = {
    "g-action-aw0092-001": "open_world", "g-action-aw0092-003": "open_world",
    "g-action-aw0092-004": "open_world", "g-action-aw0092-005": "open_world",
    "g-action-aw0092-006": "open_world", "g-action-aw0092-010": "open_world",
    "g-action-aw0092-011": "open_world", "g-action-aw0092-012": "story_campaign",
    "g-action-aw0092-013": "open_world", "g-action-aw0092-014": "open_world",
    "g-action-aw0092-015": "story_campaign", "g-adventure-action-001": "open_world",
    "g-adventure-aw0092-005": "metroidvania", "g-adventure-aw0092-008": "metroidvania",
    "g-adventure-aw0092-009": "metroidvania", "g-adventure-aw0092-015": "story_campaign",
    "g-adventure-aw0092-016": "story_campaign", "g-racing-arcade-001": "racing",
    "g-racing-arcade-002": "racing", "g-racing-sim-001": "racing",
    "g-rpg-action-001": "rpg", "g-rpg-aw0092-002": "rpg",
    "g-rpg-aw0092-003": "rpg", "g-rpg-aw0092-004": "rpg",
    "g-rpg-aw0092-005": "rpg", "g-rpg-aw0092-006": "rpg",
    "g-rpg-aw0092-009": "rpg", "g-rpg-aw0092-011": "rpg",
    "g-rpg-aw0092-012": "rpg", "g-rpg-aw0092-013": "rpg",
    "g-rpg-aw0092-014": "open_world", "g-rpg-aw0092-015": "open_world",
    "g-shooter-aw0092-006": "story_campaign", "g-shooter-aw0092-007": "open_world",
    "g-shooter-aw0092-008": "open_world", "g-shooter-aw0092-009": "open_world",
    "g-shooter-aw0092-012": "story_campaign", "g-shooter-aw0092-015": "story_campaign",
    "g-shooter-aw0092-016": "open_world", "g-shooter-fps-001": "linear_campaign",
    "g-shooter-fps-004": "rpg", "g-shooter-fps-005": "linear_campaign",
    "g-shooter-tps-001": "linear_campaign", "g-shooter-tps-003": "story_campaign",
    "g-strategy-aw0092-001": "strategy", "g-strategy-aw0092-002": "strategy",
    "g-strategy-aw0092-003": "strategy", "g-strategy-aw0092-009": "city_builder",
    "g-strategy-aw0092-010": "strategy", "g-strategy-aw0092-011": "strategy",
    "g-strategy-aw0092-012": "city_builder", "g-strategy-aw0092-014": "strategy",
    "g-strategy-aw0092-015": "strategy", "g-strategy-aw0092-016": "strategy",
    "g-strategy-rts-001": "strategy",
}

NOT_APPLICABLE = {
    "g-shooter-aw0092-001", "g-shooter-aw0092-002", "g-shooter-aw0092-003",
    "g-shooter-aw0092-004", "g-shooter-aw0092-005", "g-adventure-aw0092-001",
    "g-adventure-aw0092-002", "g-adventure-aw0092-013", "g-adventure-aw0092-014",
    "g-strategy-aw0092-004", "g-strategy-aw0092-005", "g-strategy-aw0092-006",
    "g-strategy-aw0092-007", "g-strategy-aw0092-008", "g-strategy-aw0092-013",
    "g-strategy-city-001", "g-strategy-turn-001",
}

# These need a human decision because either their structure branches heavily
# or current catalog metadata identifies the wrong release/year.
MANUAL_REVIEW = {
    "g-action-aw0092-007", "g-action-aw0092-016", "g-adventure-aw0092-003",
    "g-adventure-aw0092-004", "g-adventure-aw0092-007", "g-adventure-aw0092-011",
    "g-adventure-aw0092-012", "g-rpg-action-002", "g-rpg-aw0092-001",
    "g-rpg-aw0092-007", "g-rpg-aw0092-008", "g-rpg-aw0092-010",
    "g-rpg-aw0092-016", "g-rpg-classic-001", "g-shooter-aw0092-010",
    "g-shooter-aw0092-014",
}


def main() -> None:
    db = sqlite3.connect(CATALOG_DB)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT catalog_id,title,release_year FROM catalog_items "
        "WHERE catalog_id LIKE 'g-%' AND is_active=1 ORDER BY catalog_id"
    ).fetchall()
    db.close()

    entries = []
    for row in rows:
        game_id = str(row["catalog_id"])
        curated = CURATED.get(game_id)
        if curated:
            template_id, stages = curated
            status = "publish_ready"
        elif game_id in NOT_APPLICABLE:
            template_id, stages, status = None, (), "not_applicable"
        elif game_id in MANUAL_REVIEW:
            template_id, stages, status = None, (), "manual_review"
        else:
            template_id, stages, status = TEMPLATE_BY_ID.get(game_id), (), "template_assigned"
            if template_id is None:
                status = "manual_review"
        entries.append({
            "game_id": game_id,
            "title": row["title"],
            "release_year": row["release_year"],
            "status": status,
            "journey_template_id": template_id,
            "stages": [
                {"stage_id": f"stage-{number:02d}", "order": number, "title": title}
                for number, title in enumerate(stages, 1)
            ],
        })

    statuses = ("publish_ready", "template_assigned", "manual_review", "not_applicable")
    counts = {status: sum(item["status"] == status for item in entries) for status in statuses}
    document = {
        "format": "AW0.231 Journey Backfill 1",
        "catalog_count": len(entries),
        "counts": counts,
        "entries": entries,
    }
    OUTPUT.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(counts, ensure_ascii=False), OUTPUT)


if __name__ == "__main__":
    main()
