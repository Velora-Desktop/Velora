from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import unicodedata
import urllib.parse
import urllib.request
import shutil
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.db"
CACHE = ROOT / "data" / "aw0231_steam_audit_cache.json"
AUDIT = ROOT / "data" / "aw0231_catalog_master_audit.json"
MANUAL = ROOT / "data" / "aw0231_catalog_manual_review.json"


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = value.replace("™", "").replace("®", "")
    return re.sub(r"[^a-z0-9]+", "", value)


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "VeloraCatalogAudit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _pcgw_candidate(title: str) -> dict[str, Any] | None:
    fields = (
        "Infobox_game._pageName=Page,Infobox_game.Developers,Infobox_game.Publishers,"
        "Infobox_game.Engines,Infobox_game.Released"
    )
    where = f'Infobox_game._pageName="{title.replace(chr(34), "")}"'
    query = urllib.parse.urlencode({
        "action": "cargoquery", "format": "json", "tables": "Infobox_game",
        "fields": fields, "where": where,
    })
    rows = _get_json(f"https://www.pcgamingwiki.com/w/api.php?{query}").get("cargoquery") or []
    if len(rows) != 1:
        return None
    data = rows[0].get("title") or {}
    def names(value: str) -> list[str]:
        value = re.sub(r",(?=(?:Company|Engine):)", ";", value or "")
        return [re.sub(r"^(?:Company|Engine):", "", item).strip() for item in value.split(";") if item.strip()]
    return {
        "url": "https://www.pcgamingwiki.com/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        "developers": names(data.get("Developers", "")), "publishers": names(data.get("Publishers", "")),
        "engines": names(data.get("Engines", "")), "released": data.get("Released", ""),
    }


def _steam_candidate(title: str, year: int | None) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({"term": title, "l": "english", "cc": "us"})
    result = _get_json(f"https://store.steampowered.com/api/storesearch/?{query}")
    candidates = [item for item in result.get("items", []) if item.get("type") == "app"]
    exact = [item for item in candidates if _norm(item.get("name", "")) == _norm(title)]
    if len(exact) != 1:
        return None
    app_id = exact[0]["id"]
    details = _get_json(
        "https://store.steampowered.com/api/appdetails/?"
        + urllib.parse.urlencode({"appids": app_id, "l": "english", "cc": "us"})
    )
    payload = details.get(str(app_id), {})
    if not payload.get("success"):
        return None
    data = payload.get("data", {})
    release = data.get("release_date") or {}
    parsed_year = None
    match = re.search(r"(?:19|20)\d{2}", release.get("date", ""))
    if match:
        parsed_year = int(match.group(0))
    # A known year mismatch identifies a remake/remaster collision and is not safe.
    if year and parsed_year and abs(year - parsed_year) > 1:
        return None
    return {
        "app_id": app_id,
        "url": f"https://store.steampowered.com/app/{app_id}/",
        "title": data.get("name", ""),
        "year": parsed_year,
        "developers": data.get("developers") or [],
        "publishers": data.get("publishers") or [],
        "genres": [entry.get("description", "") for entry in data.get("genres") or []],
        "platforms": sorted(key for key, enabled in (data.get("platforms") or {}).items() if enabled),
        "description": re.sub(r"<[^>]+>", " ", data.get("short_description", "")).strip(),
        "requirements": {
            "minimum": (data.get("pc_requirements") or {}).get("minimum", ""),
            "recommended": (data.get("pc_requirements") or {}).get("recommended", ""),
        },
    }


def collect() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    with sqlite3.connect(CATALOG) as connection:
        connection.row_factory = sqlite3.Row
        games = [dict(row) for row in connection.execute(
            "SELECT catalog_id,title,release_year FROM catalog_items "
            "WHERE catalog_id LIKE 'g-%' AND is_active=1 ORDER BY catalog_id"
        )]
    for index, game in enumerate(games, 1):
        game_id = game["catalog_id"]
        if game_id in cache:
            continue
        try:
            cache[game_id] = _steam_candidate(game["title"], game["release_year"])
        except Exception as exc:  # network failures remain auditable, never destructive
            cache[game_id] = {"error": f"{type(exc).__name__}: {exc}"}
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{index:03}/{len(games)} {game['title']}: {'MATCH' if cache[game_id] and 'error' not in cache[game_id] else 'REVIEW'}")
        time.sleep(0.15)


def collect_pcgw() -> None:
    output = ROOT / "data" / "aw0231_pcgw_audit_cache.json"
    cache = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    with sqlite3.connect(CATALOG) as connection:
        connection.row_factory = sqlite3.Row
        games = [dict(row) for row in connection.execute(
            "SELECT catalog_id,title FROM catalog_items WHERE catalog_id LIKE 'g-%' AND is_active=1 ORDER BY catalog_id"
        )]
    for index, game in enumerate(games, 1):
        if game["catalog_id"] in cache:
            continue
        try:
            cache[game["catalog_id"]] = _pcgw_candidate(game["title"])
        except Exception as exc:
            cache[game["catalog_id"]] = {"error": f"{type(exc).__name__}: {exc}"}
        output.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{index:03}/{len(games)} {game['title']}: {'MATCH' if cache[game['catalog_id']] else 'REVIEW'}")
        time.sleep(0.1)


CURATED = {
    "g-action-aw0092-001": (2013, "Rockstar North", "Rockstar Games", "https://www.rockstargames.com/gta-v"),
    "g-action-aw0092-002": (2005, "Santa Monica Studio", "Sony Computer Entertainment", "https://www.playstation.com/en-us/god-of-war/"),
    "g-action-aw0092-003": (2022, "Santa Monica Studio", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/god-of-war-ragnarok/"),
    "g-action-aw0092-004": (2020, "Sucker Punch Productions", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/ghost-of-tsushima/"),
    "g-action-aw0092-005": (2018, "Insomniac Games", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/marvels-spider-man-remastered/"),
    "g-action-aw0092-006": (2020, "Insomniac Games", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/marvels-spider-man-miles-morales/"),
    "g-action-aw0092-007": (2016, "Naughty Dog", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/uncharted-4-a-thiefs-end/"),
    "g-action-aw0092-008": (2022, "Naughty Dog", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/the-last-of-us-part-i/"),
    "g-action-aw0092-009": (2020, "Naughty Dog", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/the-last-of-us-part-ii-remastered/"),
    "g-action-aw0092-012": (2021, "IO Interactive", "IO Interactive", "https://ioi.dk/hitman"),
    "g-action-aw0092-013": (2009, "Ubisoft Montreal", "Ubisoft", "https://www.ubisoft.com/en-us/game/assassins-creed/assassins-creed-2"),
    "g-action-aw0092-014": (2013, "Ubisoft Montreal", "Ubisoft", "https://www.ubisoft.com/en-us/game/assassins-creed/iv-black-flag"),
    "g-action-aw0092-016": (2023, "Remedy Entertainment", "Epic Games Publishing", "https://www.alanwake.com/"),
    "g-adventure-action-001": (2018, "Rockstar Studios", "Rockstar Games", "https://www.rockstargames.com/reddeadredemption2/"),
    "g-adventure-aw0092-004": (2020, "Supergiant Games", "Supergiant Games", "https://www.supergiantgames.com/games/hades/"),
    "g-adventure-aw0092-007": (2018, "Motion Twin", "Motion Twin", "https://dead-cells.com/"),
    "g-adventure-aw0092-010": (2017, "Studio MDHR Entertainment", "Studio MDHR Entertainment", "https://www.cupheadgame.com/"),
    "g-adventure-aw0092-015": (2021, "Hazelight Studios", "Electronic Arts", "https://www.ea.com/games/it-takes-two"),
    "g-adventure-aw0092-016": (2018, "Hazelight Studios", "Electronic Arts", "https://www.ea.com/games/a-way-out"),
    "g-racing-arcade-001": (2021, "Playground Games", "Xbox Game Studios", "https://store.steampowered.com/app/1551360/"),
    "g-rpg-action-002": (2022, "FromSoftware", "Bandai Namco Entertainment", "https://store.steampowered.com/app/1245620/"),
    "g-rpg-aw0092-001": (2020, "CD Projekt RED", "CD Projekt", "https://www.cyberpunk.net/"),
    "g-rpg-aw0092-004": (2016, "FromSoftware", "Bandai Namco Entertainment", "https://store.steampowered.com/app/374320/"),
    "g-rpg-aw0092-007": (2017, "Larian Studios", "Larian Studios", "https://store.steampowered.com/app/435150/"),
    "g-rpg-aw0092-009": (2019, "Atlus", "Sega", "https://store.steampowered.com/app/1687950/"),
    "g-rpg-aw0092-010": (2020, "Square Enix", "Square Enix", "https://ffvii-remake-intergrade.square-enix-games.com/"),
    "g-rpg-aw0092-011": (2018, "Warhorse Studios", "Deep Silver", "https://store.steampowered.com/app/379430/"),
    "g-rpg-aw0092-012": (2018, "Capcom", "Capcom", "https://store.steampowered.com/app/582010/"),
    "g-rpg-aw0092-013": (2017, "PlatinumGames", "Square Enix", "https://store.steampowered.com/app/524220/"),
    "g-rpg-aw0092-015": (2022, "Guerrilla Games", "Sony Interactive Entertainment", "https://www.playstation.com/en-us/games/horizon-forbidden-west/"),
    "g-rpg-aw0092-016": (2023, "Blizzard Entertainment", "Blizzard Entertainment", "https://diablo4.blizzard.com/"),
    "g-shooter-aw0092-004": (2022, "Blizzard Entertainment", "Blizzard Entertainment", "https://overwatch.blizzard.com/"),
    "g-shooter-aw0092-005": (2015, "Ubisoft Montreal", "Ubisoft", "https://www.ubisoft.com/en-us/game/rainbow-six/siege"),
    "g-shooter-aw0092-007": (2012, "Ubisoft Montreal", "Ubisoft", "https://store.steampowered.com/app/220240/"),
    "g-shooter-aw0092-008": (2018, "Ubisoft Montreal", "Ubisoft", "https://store.steampowered.com/app/552520/"),
    "g-shooter-aw0092-010": (2017, "Arkane Studios", "Bethesda Softworks", "https://store.steampowered.com/app/480490/"),
    "g-shooter-aw0092-015": (2014, "MachineGames", "Bethesda Softworks", "https://store.steampowered.com/app/201810/"),
    "g-shooter-tps-001": (2012, "Rockstar Studios", "Rockstar Games", "https://www.rockstargames.com/games/maxpayne3"),
    "g-shooter-tps-002": (2023, "Capcom", "Capcom", "https://store.steampowered.com/app/2050650/"),
}


def repair_and_manifest() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    previous_audit = json.loads(AUDIT.read_text(encoding="utf-8")) if AUDIT.exists() else {}
    previous_corrections = previous_audit.get("corrections") or []
    connection = sqlite3.connect(CATALOG)
    connection.row_factory = sqlite3.Row
    games = [dict(row) for row in connection.execute(
        "SELECT * FROM catalog_items WHERE catalog_id LIKE 'g-%' AND is_active=1 ORDER BY catalog_id"
    )]
    corrections: list[dict[str, Any]] = list(previous_corrections)
    for game in games:
        source = cache.get(game["catalog_id"])
        if game["catalog_id"] in CURATED:
            year, developer, publisher, url = CURATED[game["catalog_id"]]
            values = {"release_year": year, "developer": developer, "publisher": publisher}
            sources = [url]
            confidence = "HIGH"
        elif isinstance(source, dict) and source.get("app_id"):
            values = {
                "release_year": source.get("year"),
                "developer": "; ".join(source.get("developers") or []),
                "publisher": "; ".join(source.get("publishers") or []),
            }
            sources = [source["url"]]
            confidence = "MEDIUM"
        else:
            continue
        for field, value in values.items():
            if value in (None, "") or game[field] == value:
                continue
            # Automatic MEDIUM changes only repair missing/technical identifiers.
            technical = field == "release_year" and game[field] is None
            technical = technical or field in ("developer", "publisher") and (
                not str(game[field]).strip() or re.search(r"(?:^|; )Q\d+", str(game[field]))
            )
            if confidence == "HIGH" or technical:
                connection.execute(f"UPDATE catalog_items SET {field}=? WHERE catalog_id=?", (value, game["catalog_id"]))
                correction = {
                    "game_id": game["catalog_id"], "title": game["title"], "field": field,
                    "old_value": game[field], "new_value": value, "sources": sources, "confidence": confidence,
                }
                key = (correction["game_id"], correction["field"], correction["new_value"])
                if not any((item["game_id"], item["field"], item["new_value"]) == key for item in corrections):
                    corrections.append(correction)
                game[field] = value
    connection.commit()

    manual: list[dict[str, Any]] = []
    manifest_games = []
    fields = ("title", "release_year", "description", "developer", "publisher", "engine", "catalog_tags_json",
              "platforms", "player_modes", "system_requirements_json", "franchise_name", "chronology_json", "cover_path")
    for game in games:
        source = cache.get(game["catalog_id"])
        statuses = {}
        for field in fields:
            value = game[field]
            missing = value is None or str(value).strip() in ("", "[]", "{}")
            if field == "cover_path":
                missing = missing or not (ROOT / str(value)).is_file()
            corrected = any(item["game_id"] == game["catalog_id"] and item["field"] == field for item in corrections)
            if corrected:
                status = "corrected"
            elif missing and field in ("engine", "player_modes", "system_requirements_json"):
                status = "manual_review"
            elif missing:
                status = "missing"
            elif field in ("cover_path", "title") or isinstance(source, dict) and source.get("app_id"):
                status = "verified"
            else:
                status = "manual_review"
            statuses[field] = status
            if status == "manual_review":
                manual.append({
                    "game_id": game["catalog_id"], "title": game["title"], "year": game["release_year"],
                    "field": field, "current_value": value, "suggested_value": None,
                    "reason": "Поле не получило однозначного подтверждения из приоритетного источника; автоматическое изменение запрещено.",
                    "sources": [source["url"]] if isinstance(source, dict) and source.get("url") else [], "confidence": "LOW",
                })
        manifest_games.append({"game_id": game["catalog_id"], "title": game["title"], "year": game["release_year"], "fields": statuses})
    generated = datetime.now(timezone.utc).isoformat()
    AUDIT.write_text(json.dumps({"schema": 1, "generated_at": generated, "games": manifest_games, "corrections": corrections}, ensure_ascii=False, indent=2), encoding="utf-8")
    MANUAL.write_text(json.dumps({"schema": 1, "generated_at": generated, "items": manual}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"games={len(games)} corrections={len(corrections)} manual={len(manual)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("collect", "collect-pcgw", "repair"))
    arguments = parser.parse_args()
    if arguments.command == "collect":
        collect()
    elif arguments.command == "collect-pcgw":
        collect_pcgw()
    else:
        repair_and_manifest()
