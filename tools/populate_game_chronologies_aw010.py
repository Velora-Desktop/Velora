from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.db"
BACKUP = ROOT / "data" / "catalog.before_aw010_chronology.db"

# Release chronology. Entries without catalog_id remain visible as external/upcoming titles.
SERIES: dict[str, list[tuple[str, int | None, str]]] = {
    "Doom": [
        ("Doom", 1993, ""), ("Doom II: Hell on Earth", 1994, ""),
        ("Final Doom", 1996, ""), ("Doom 64", 1997, ""), ("Doom 3", 2004, ""),
        ("Doom", 2016, ""), ("Doom Eternal", 2020, ""),
        ("Doom: The Dark Ages", 2025, "вышла"),
    ],
    "BioShock": [
        ("BioShock", 2007, ""), ("BioShock 2", 2010, ""),
        ("BioShock Infinite", 2013, ""), ("BioShock 4", None, "анонсирована"),
    ],
    "Borderlands": [
        ("Borderlands", 2009, ""), ("Borderlands 2", 2012, ""),
        ("Borderlands: The Pre-Sequel", 2014, ""), ("Borderlands 3", 2019, ""),
        ("New Tales from the Borderlands", 2022, ""), ("Borderlands 4", 2025, "вышла"),
    ],
    "Call of Duty": [
        ("Call of Duty", 2003, ""), ("Call of Duty 2", 2005, ""),
        ("Call of Duty 3", 2006, ""), ("Call of Duty 4: Modern Warfare", 2007, ""),
        ("Call of Duty: World at War", 2008, ""), ("Call of Duty: Modern Warfare 2", 2009, ""),
        ("Call of Duty: Black Ops", 2010, ""), ("Call of Duty: Modern Warfare 3", 2011, ""),
    ],
    "Dishonored": [
        ("Dishonored", 2012, ""), ("Dishonored 2", 2016, ""),
        ("Dishonored: Death of the Outsider", 2017, ""),
    ],
    "Far Cry": [
        ("Far Cry", 2004, ""), ("Far Cry 2", 2008, ""), ("Far Cry 3", 2012, ""),
        ("Far Cry 4", 2014, ""), ("Far Cry 5", 2018, ""),
        ("Far Cry New Dawn", 2019, ""), ("Far Cry 6", 2021, ""),
    ],
    "God of War": [
        ("God of War", 2005, ""), ("God of War II", 2007, ""),
        ("God of War III", 2010, ""), ("God of War: Ascension", 2013, ""),
        ("God of War", 2018, ""), ("God of War Ragnarök", 2022, ""),
    ],
    "Horizon": [
        ("Horizon Zero Dawn", 2017, ""), ("Horizon Forbidden West", 2022, ""),
        ("LEGO Horizon Adventures", 2024, ""),
    ],
    "Marvel's Spider-Man": [
        ("Marvel's Spider-Man", 2018, ""),
        ("Marvel's Spider-Man: Miles Morales", 2020, ""),
        ("Marvel's Spider-Man 2", 2023, ""),
        ("Marvel's Wolverine", 2026, "ожидается"),
    ],
    "Ori": [
        ("Ori and the Blind Forest", 2015, ""),
        ("Ori and the Will of the Wisps", 2020, ""),
    ],
    "The Last of Us": [
        ("The Last of Us", 2013, ""), ("The Last of Us Part II", 2020, ""),
        ("The Last of Us Part I", 2022, ""),
    ],
    "Assassin's Creed": [
        ("Assassin's Creed", 2007, ""), ("Assassin's Creed II", 2009, ""),
        ("Assassin's Creed Brotherhood", 2010, ""), ("Assassin's Creed Revelations", 2011, ""),
        ("Assassin's Creed III", 2012, ""), ("Assassin's Creed IV: Black Flag", 2013, ""),
        ("Assassin's Creed Origins", 2017, ""), ("Assassin's Creed Odyssey", 2018, ""),
        ("Assassin's Creed Valhalla", 2020, ""), ("Assassin's Creed Shadows", 2025, ""),
    ],
    "Alan Wake": [
        ("Alan Wake", 2010, ""), ("Alan Wake's American Nightmare", 2012, ""),
        ("Alan Wake 2", 2023, ""),
    ],
    "Cities: Skylines": [
        ("Cities: Skylines", 2015, ""), ("Cities: Skylines II", 2023, ""),
    ],
    "Dark Souls": [
        ("Dark Souls", 2011, ""), ("Dark Souls II", 2014, ""), ("Dark Souls III", 2016, ""),
    ],
    "Divinity": [
        ("Divinity: Original Sin", 2014, ""), ("Divinity: Original Sin 2", 2017, ""),
    ],
    "Dragon Age": [
        ("Dragon Age: Origins", 2009, ""), ("Dragon Age II", 2011, ""),
        ("Dragon Age: Inquisition", 2014, ""), ("Dragon Age: The Veilguard", 2024, ""),
    ],
    "Fallout": [
        ("Fallout", 1997, ""), ("Fallout 2", 1998, ""), ("Fallout 3", 2008, ""),
        ("Fallout: New Vegas", 2010, ""), ("Fallout 4", 2015, ""), ("Fallout 76", 2018, ""),
    ],
    "Forza Horizon": [
        ("Forza Horizon", 2012, ""), ("Forza Horizon 2", 2014, ""),
        ("Forza Horizon 3", 2016, ""), ("Forza Horizon 4", 2018, ""),
        ("Forza Horizon 5", 2021, ""),
    ],
    "Half-Life": [
        ("Half-Life", 1998, ""), ("Half-Life 2", 2004, ""),
        ("Half-Life 2: Episode One", 2006, ""), ("Half-Life 2: Episode Two", 2007, ""),
        ("Half-Life: Alyx", 2020, ""),
    ],
    "Hitman": [
        ("Hitman: Codename 47", 2000, ""), ("Hitman 2: Silent Assassin", 2002, ""),
        ("Hitman: Contracts", 2004, ""), ("Hitman: Blood Money", 2006, ""),
        ("Hitman: Absolution", 2012, ""), ("Hitman", 2016, ""),
        ("Hitman 2", 2018, ""), ("Hitman 3", 2021, ""),
    ],
    "Max Payne": [
        ("Max Payne", 2001, ""), ("Max Payne 2: The Fall of Max Payne", 2003, ""),
        ("Max Payne 3", 2012, ""),
    ],
    "Metro": [
        ("Metro 2033", 2010, ""), ("Metro: Last Light", 2013, ""),
        ("Metro Exodus", 2019, ""), ("Metro Awakening", 2024, ""),
    ],
    "Need for Speed": [
        ("The Need for Speed", 1994, ""), ("Need for Speed: Underground", 2003, ""),
        ("Need for Speed: Underground 2", 2004, ""), ("Need for Speed: Most Wanted", 2005, ""),
        ("Need for Speed: Heat", 2019, ""), ("Need for Speed Unbound", 2022, ""),
    ],
    "Red Dead Redemption": [
        ("Red Dead Revolver", 2004, ""), ("Red Dead Redemption", 2010, ""),
        ("Red Dead Redemption 2", 2018, ""),
    ],
    "Resident Evil": [
        ("Resident Evil", 1996, ""), ("Resident Evil 2", 1998, ""),
        ("Resident Evil 3: Nemesis", 1999, ""), ("Resident Evil 4", 2005, ""),
        ("Resident Evil 5", 2009, ""), ("Resident Evil 6", 2012, ""),
        ("Resident Evil 7: Biohazard", 2017, ""), ("Resident Evil Village", 2021, ""),
        ("Resident Evil Requiem", 2026, "ожидается"),
    ],
    "S.T.A.L.K.E.R.": [
        ("S.T.A.L.K.E.R.: Shadow of Chernobyl", 2007, ""),
        ("S.T.A.L.K.E.R.: Clear Sky", 2008, ""),
        ("S.T.A.L.K.E.R.: Call of Pripyat", 2009, ""),
        ("S.T.A.L.K.E.R. 2: Heart of Chornobyl", 2024, ""),
    ],
    "The Elder Scrolls": [
        ("The Elder Scrolls: Arena", 1994, ""), ("The Elder Scrolls II: Daggerfall", 1996, ""),
        ("The Elder Scrolls III: Morrowind", 2002, ""), ("The Elder Scrolls IV: Oblivion", 2006, ""),
        ("The Elder Scrolls V: Skyrim", 2011, ""), ("The Elder Scrolls VI", None, "анонсирована"),
    ],
    "The Witcher": [
        ("The Witcher", 2007, ""), ("The Witcher 2: Assassins of Kings", 2011, ""),
        ("The Witcher 3", 2015, ""), ("The Witcher IV", None, "анонсирована"),
    ],
    "Titanfall": [
        ("Titanfall", 2014, ""), ("Titanfall 2", 2016, ""), ("Apex Legends", 2019, ""),
    ],
    "Wolfenstein": [
        ("Wolfenstein 3D", 1992, ""), ("Return to Castle Wolfenstein", 2001, ""),
        ("Wolfenstein", 2009, ""), ("Wolfenstein: The New Order", 2014, ""),
        ("Wolfenstein: The Old Blood", 2015, ""), ("Wolfenstein II: The New Colossus", 2017, ""),
        ("Wolfenstein: Youngblood", 2019, ""),
    ],
    "Diablo": [
        ("Diablo", 1997, ""), ("Diablo II", 2000, ""), ("Diablo III", 2012, ""),
        ("Diablo Immortal", 2022, ""), ("Diablo IV", 2023, ""),
    ],
    "Grand Theft Auto": [
        ("Grand Theft Auto", 1997, ""), ("Grand Theft Auto III", 2001, ""),
        ("Grand Theft Auto: Vice City", 2002, ""), ("Grand Theft Auto: San Andreas", 2004, ""),
        ("Grand Theft Auto IV", 2008, ""), ("Grand Theft Auto V", 2013, ""),
        ("Grand Theft Auto VI", 2026, "ожидается"),
    ],
    "Death Stranding": [
        ("Death Stranding", 2019, ""), ("Death Stranding 2: On the Beach", 2025, ""),
    ],
    "Age of Empires": [
        ("Age of Empires", 1997, ""), ("Age of Empires II", 1999, ""),
        ("Age of Empires III", 2005, ""), ("Age of Empires IV", 2021, ""),
        ("Age of Empires II: Definitive Edition", 2019, ""),
    ],
    "Anno": [
        ("Anno 1602", 1998, ""), ("Anno 1503", 2002, ""), ("Anno 1701", 2006, ""),
        ("Anno 1404", 2009, ""), ("Anno 2070", 2011, ""), ("Anno 2205", 2015, ""),
        ("Anno 1800", 2019, ""), ("Anno 117: Pax Romana", 2025, ""),
    ],
    "Baldur's Gate": [
        ("Baldur's Gate", 1998, ""), ("Baldur's Gate II: Shadows of Amn", 2000, ""),
        ("Baldur's Gate 3", 2023, ""),
    ],
    "Command & Conquer": [
        ("Command & Conquer", 1995, ""), ("Command & Conquer: Red Alert", 1996, ""),
        ("Command & Conquer: Tiberian Sun", 1999, ""), ("Command & Conquer: Generals", 2003, ""),
        ("Command & Conquer 3: Tiberium Wars", 2007, ""),
        ("Command & Conquer Remastered Collection", 2020, ""),
    ],
    "Company of Heroes": [
        ("Company of Heroes", 2006, ""), ("Company of Heroes 2", 2013, ""),
        ("Company of Heroes 3", 2023, ""),
    ],
    "Counter-Strike": [
        ("Counter-Strike", 2000, ""), ("Counter-Strike: Condition Zero", 2004, ""),
        ("Counter-Strike: Source", 2004, ""), ("Counter-Strike: Global Offensive", 2012, ""),
        ("Counter-Strike 2", 2023, ""),
    ],
    "Crusader Kings": [
        ("Crusader Kings", 2004, ""), ("Crusader Kings II", 2012, ""),
        ("Crusader Kings III", 2020, ""),
    ],
    "Cyberpunk": [
        ("Cyberpunk 2077", 2020, ""), ("Project Orion", None, "в разработке"),
    ],
    "Final Fantasy VII Remake": [
        ("Final Fantasy VII Remake", 2020, ""), ("Final Fantasy VII Rebirth", 2024, ""),
        ("Final Fantasy VII Remake Part 3", None, "в разработке"),
    ],
    "Frostpunk": [
        ("Frostpunk", 2018, ""), ("Frostpunk 2", 2024, ""),
    ],
    "Gran Turismo": [
        ("Gran Turismo", 1997, ""), ("Gran Turismo 2", 1999, ""), ("Gran Turismo 3: A-Spec", 2001, ""),
        ("Gran Turismo 4", 2004, ""), ("Gran Turismo 5", 2010, ""), ("Gran Turismo 6", 2013, ""),
        ("Gran Turismo Sport", 2017, ""), ("Gran Turismo 7", 2022, ""),
    ],
    "Hades": [
        ("Hades", 2020, ""), ("Hades II", 2025, ""),
    ],
    "Kingdom Come": [
        ("Kingdom Come: Deliverance", 2018, ""), ("Kingdom Come: Deliverance II", 2025, ""),
    ],
    "Mass Effect": [
        ("Mass Effect", 2007, ""), ("Mass Effect 2", 2010, ""), ("Mass Effect 3", 2012, ""),
        ("Mass Effect: Andromeda", 2017, ""), ("Mass Effect Legendary Edition", 2021, ""),
        ("Next Mass Effect", None, "анонсирована"),
    ],
    "Metal Gear Solid": [
        ("Metal Gear Solid", 1998, ""), ("Metal Gear Solid 2: Sons of Liberty", 2001, ""),
        ("Metal Gear Solid 3: Snake Eater", 2004, ""), ("Metal Gear Solid 4: Guns of the Patriots", 2008, ""),
        ("Metal Gear Solid V: Ground Zeroes", 2014, ""),
        ("Metal Gear Solid V: The Phantom Pain", 2015, ""), ("Metal Gear Solid Delta: Snake Eater", 2025, ""),
    ],
    "Monster Hunter": [
        ("Monster Hunter", 2004, ""), ("Monster Hunter 2", 2006, ""), ("Monster Hunter Tri", 2009, ""),
        ("Monster Hunter 4", 2013, ""), ("Monster Hunter: World", 2018, ""),
        ("Monster Hunter Rise", 2021, ""), ("Monster Hunter Wilds", 2025, ""),
    ],
    "NieR": [
        ("NieR", 2010, ""), ("NieR: Automata", 2017, ""), ("NieR Replicant ver.1.22474487139...", 2021, ""),
    ],
    "Overwatch": [
        ("Overwatch", 2016, ""), ("Overwatch 2", 2022, ""),
    ],
    "Persona 5": [
        ("Persona 5", 2016, ""), ("Persona 5 Royal", 2019, ""),
        ("Persona 5 Strikers", 2020, ""), ("Persona 5 Tactica", 2023, ""),
    ],
    "Sid Meier's Civilization": [
        ("Sid Meier's Civilization", 1991, ""), ("Civilization II", 1996, ""),
        ("Civilization III", 2001, ""), ("Civilization IV", 2005, ""),
        ("Civilization V", 2010, ""), ("Sid Meier's Civilization VI", 2016, ""),
        ("Sid Meier's Civilization VII", 2025, ""),
    ],
    "StarCraft": [
        ("StarCraft", 1998, ""), ("StarCraft: Brood War", 1998, ""),
        ("StarCraft II", 2010, ""), ("StarCraft II: Heart of the Swarm", 2013, ""),
        ("StarCraft II: Legacy of the Void", 2015, ""),
    ],
    "Subnautica": [
        ("Subnautica", 2018, ""), ("Subnautica: Below Zero", 2021, ""),
        ("Subnautica 2", None, "в разработке"),
    ],
    "Warcraft": [
        ("Warcraft: Orcs & Humans", 1994, ""), ("Warcraft II: Tides of Darkness", 1995, ""),
        ("Warcraft III", 2002, ""), ("Warcraft III: The Frozen Throne", 2003, ""),
        ("Warcraft III: Reforged", 2020, ""),
    ],
    "Medal of Honor": [
        ("Medal of Honor", 1999, ""), ("Medal of Honor: Underground", 2000, ""),
        ("Medal of Honor: Allied Assault", 2002, ""), ("Medal of Honor: Frontline", 2002, ""),
        ("Medal of Honor: Rising Sun", 2003, ""), ("Medal of Honor: Pacific Assault", 2004, ""),
        ("Medal of Honor: European Assault", 2005, ""), ("Medal of Honor: Airborne", 2007, ""),
        ("Medal of Honor (2010)", 2010, ""), ("Medal of Honor: Warfighter", 2012, ""),
    ],
    "Tom Clancy's Rainbow Six": [
        ("Tom Clancy's Rainbow Six", 1998, ""), ("Rainbow Six: Rogue Spear", 1999, ""),
        ("Rainbow Six 3: Raven Shield", 2003, ""), ("Rainbow Six: Vegas", 2006, ""),
        ("Rainbow Six: Vegas 2", 2008, ""), ("Tom Clancy's Rainbow Six Siege", 2015, ""),
    ],
    "XCOM": [
        ("X-COM: UFO Defense", 1994, ""), ("XCOM: Enemy Unknown", 2012, ""),
        ("XCOM 2", 2016, ""), ("XCOM: Chimera Squad", 2020, ""),
    ],
    "Uncharted": [
        ("Uncharted: Drake's Fortune", 2007, ""), ("Uncharted 2: Among Thieves", 2009, ""),
        ("Uncharted 3: Drake's Deception", 2011, ""), ("Uncharted 4: A Thief's End", 2016, ""),
        ("Uncharted: The Lost Legacy", 2017, ""),
    ],
    "Control": [
        ("Control", 2019, ""), ("FBC: Firebreak", 2025, ""),
        ("Control Resonant", None, "в разработке"),
    ],
    "Hollow Knight": [
        ("Hollow Knight", 2017, ""), ("Hollow Knight: Silksong", 2025, ""),
    ],
    "Ghost": [
        ("Ghost of Tsushima", 2020, ""), ("Ghost of Yōtei", 2025, ""),
    ],
    "Total War: Warhammer": [
        ("Total War: Warhammer", 2016, ""), ("Total War: Warhammer II", 2017, ""),
        ("Total War: Warhammer III", 2022, ""),
    ],
    "Elden Ring": [
        ("Elden Ring", 2022, ""), ("Elden Ring Nightreign", 2025, ""),
    ],
}


def main() -> None:
    if not BACKUP.exists(): shutil.copy2(CATALOG, BACKUP)
    connection = sqlite3.connect(CATALOG)
    connection.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(catalog_items)")}
        if "franchise_name" not in columns:
            connection.execute("ALTER TABLE catalog_items ADD COLUMN franchise_name TEXT NOT NULL DEFAULT ''")
        if "chronology_json" not in columns:
            connection.execute("ALTER TABLE catalog_items ADD COLUMN chronology_json TEXT NOT NULL DEFAULT '[]'")
        games = connection.execute(
            "SELECT catalog_id,title,cover_path FROM catalog_items WHERE catalog_id LIKE 'g-%'"
        ).fetchall()
        by_title = {row["title"].casefold(): row for row in games}
        updated: set[str] = set()
        for franchise, raw_entries in SERIES.items():
            entries: list[dict[str, object]] = []
            linked_ids: list[str] = []
            for position, (title, year, status) in enumerate(raw_entries, 1):
                match = by_title.get(title.casefold())
                catalog_id = match["catalog_id"] if match else ""
                cover_path = match["cover_path"] if match else ""
                if catalog_id: linked_ids.append(catalog_id)
                entries.append({
                    "position": position, "title": title, "release_year": year or "",
                    "catalog_id": catalog_id, "cover_path": cover_path or "",
                    "status": status or ("в каталоге" if catalog_id else "нет в каталоге"),
                })
            payload = json.dumps(entries, ensure_ascii=False)
            for catalog_id in linked_ids:
                connection.execute(
                    "UPDATE catalog_items SET franchise_name=?,chronology_json=? WHERE catalog_id=?",
                    (franchise, payload, catalog_id),
                )
                updated.add(catalog_id)
        connection.commit()
        print(f"Связано карточек: {len(updated)}; серий: {len(SERIES)}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
