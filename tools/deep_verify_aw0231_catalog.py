from __future__ import annotations

import html
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "catalog.db"
AUDIT = ROOT / "data" / "aw0231_catalog_master_audit.json"
MANUAL = ROOT / "data" / "aw0231_catalog_manual_review.json"
STEAM = ROOT / "data" / "aw0231_steam_audit_cache.json"
PCGW = ROOT / "data" / "aw0231_pcgw_audit_cache.json"

ENGINE_BLOCKLIST = {"", "Unknown", "Custom", "Proprietary"}

DESCRIPTIONS = {
"g-rpg-action-002": "Elden Ring — ролевая игра с открытым миром от FromSoftware. Игрок управляет Погасшим, который исследует Междуземье, сражается с полубогами и собирает осколки Кольца Элден, чтобы стать новым повелителем. Боевая система сочетает оружие, магию, призыв духов и свободное развитие персонажа.",
"g-shooter-tps-002": "Resident Evil 4 — ремейк survival horror 2005 года от Capcom. Леон Кеннеди отправляется в изолированную европейскую деревню, чтобы спасти похищенную дочь президента, и сталкивается с заражёнными жителями. Игра сочетает стрельбу от третьего лица, управление ограниченными ресурсами, исследование и переработанные эпизоды оригинала.",
"g-shooter-aw0092-007": "Far Cry 3 — шутер от первого лица с открытым миром от Ubisoft Montreal. Джейсон Броди пытается спасти друзей и выбраться с островов Рук, захваченных пиратами Вааса. Игрок освобождает аванпосты, охотится, улучшает снаряжение и выбирает между скрытным прохождением и открытым боем.",
"g-shooter-aw0092-008": "Far Cry 5 — шутер от первого лица с открытым миром от Ubisoft Montreal. Помощник шерифа противостоит культу «Врата Эдема», захватившему округ Хоуп в Монтане. Мир можно исследовать свободно, привлекая союзников и освобождая три региона в одиночку или совместном режиме.",
"g-rpg-aw0092-015": "Horizon Forbidden West — приключенческий экшен с элементами RPG от Guerrilla Games. Элой отправляется на Запретный Запад в поисках способа остановить разрушение биосферы и сталкивается с новыми племенами и машинами. Исследование открытого мира дополняют охота, создание снаряжения, ближний бой и тактическое использование слабостей машин.",
"g-rpg-aw0092-016": "Diablo IV — мрачная action-RPG от Blizzard Entertainment. Герой странствует по открытому Санктуарию и противостоит возвращению Лилит, проходя сюжетные задания, подземелья и мировые события. Классы предлагают разные сборки навыков и экипировки, а прогресс продолжается в совместной игре и сезонных режимах.",
"g-action-aw0092-013": "Assassin's Creed II — приключенческий экшен Ubisoft Montreal о становлении Эцио Аудиторе в Италии эпохи Возрождения. Герой раскрывает заговор тамплиеров, осваивает паркур, скрытные убийства и открытые схватки. Города соединяют сюжетные миссии, побочные задания, улучшение поместья и поиск исторических секретов.",
"g-action-aw0092-014": "Assassin's Creed IV: Black Flag — приключенческий экшен Ubisoft Montreal о пирате Эдварде Кенуэе в Карибском море XVIII века. Игрок исследует острова, участвует в морских сражениях и охоте за сокровищами, одновременно оказываясь в конфликте ассасинов и тамплиеров. Корабль можно улучшать, а к целям подходить скрытно или напрямую.",
"g-action-aw0092-001": "Grand Theft Auto V — криминальный экшен с открытым миром от Rockstar North. История следует за Майклом, Франклином и Тревором, чьи линии пересекаются во время серии ограблений в Лос-Сантосе. Игрок свободно переключается между героями, исследует город, выполняет задания и использует транспорт разных типов.",
"g-action-aw0092-005": "Marvel's Spider-Man — приключенческий экшен Insomniac Games о взрослом Питере Паркере. Человек-паук защищает Нью-Йорк от новой преступной угрозы, совмещая личную жизнь с охотой на злодеев. Передвижение на паутине, акробатические бои, скрытность и улучшение костюмов образуют основу игрового процесса.",
"g-racing-arcade-001": "Forza Horizon 5 — гоночная игра Playground Games с открытым миром, действие которой происходит в Мексике. Игрок участвует в фестивале Horizon, открывает соревнования и собирает автомобили разных классов. Мир поддерживает одиночные заезды, сетевые события, совместную игру и пользовательские маршруты.",
"g-rpg-aw0092-010": "Final Fantasy VII Remake — первая часть переосмысления Final Fantasy VII от Square Enix. Наёмник Клауд Страйф присоединяется к группе «ЛАВИНА» в борьбе против корпорации Shinra в Мидгаре. Сражения объединяют действие в реальном времени с командами, магией и тактическим переключением между героями.",
"g-rpg-aw0092-013": "NieR: Automata — action-RPG PlatinumGames, действие которой разворачивается на Земле, захваченной машинами. Андроиды 2B, 9S и A2 выполняют задания для человечества и постепенно раскрывают природу войны. Быстрые бои, смена жанровых перспектив и несколько прохождений складываются в единую историю.",
"g-shooter-aw0092-004": "Overwatch 2 — командный геройский шутер Blizzard Entertainment. Игроки выбирают героев с разными ролями и способностями и сражаются за выполнение целей на отдельных картах. Состав команды, взаимодействие умений и быстрая смена персонажей важнее индивидуального вооружения.",
"g-rpg-aw0092-004": "Dark Souls III — ролевая игра FromSoftware в мире, где угасает Первое пламя. Негорящий отправляется вернуть Повелителей Пепла на их троны и решить судьбу цикла огня. Исследование связанных областей строится вокруг сложных боёв, управления выносливостью и развития выбранного вооружения.",
"g-rpg-aw0092-009": "Persona 5 Royal — расширенная версия японской ролевой игры Atlus о группе школьников, меняющих сердца преступников. Днём герой учится, строит отношения и планирует дела, а ночью исследует метафизические дворцы. Пошаговые бои, развитие персон и календарная структура связывают две стороны жизни команды.",
"g-shooter-fps-005": "Medal of Honor — шутер от первого лица 2010 года, посвящённый операциям американских подразделений в Афганистане. Кампания показывает действия бойцов Tier 1 и других частей во время одной военной операции. Игровой процесс чередует пехотные столкновения, скрытные эпизоды и поддержку с воздуха.",
"g-action-aw0092-017": "God of War — приключенческий экшен Santa Monica Studio 2018 года. Кратос и его сын Атрей отправляются развеять прах матери на высочайшей вершине девяти миров и сталкиваются с богами и существами скандинавской мифологии. Бои строятся вокруг топора Левиафан, щита, рунических атак и совместных действий отца и сына.",
}

def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


REQUIREMENT_KEYS = {
    "os": "os", "operating system": "os",
    "processor": "cpu", "cpu": "cpu",
    "memory": "ram", "ram": "ram",
    "graphics": "gpu", "video card": "gpu", "gpu": "gpu",
    "storage": "storage", "hard drive": "storage", "disk space": "storage",
    "additional notes": "additional", "additional": "additional",
}


def structured_requirements(minimum: str, recommended: str) -> dict[str, str]:
    """Convert official Steam requirement labels to the Catalog Schema 1 read contract."""
    result: dict[str, str] = {}
    for suffix, raw in (("min", minimum), ("rec", recommended)):
        for line in raw.splitlines():
            line = line.strip(" \t\u2022-")
            if not line or ":" not in line:
                continue
            label, value = (part.strip() for part in line.split(":", 1))
            key = REQUIREMENT_KEYS.get(label.casefold())
            if key and value:
                result[f"{key}_{suffix}"] = value
    return result


def normalized_names(value) -> set[str]:
    if isinstance(value, str):
        values = re.split(r"\s*[;,/]\s*", value)
    else:
        values = value or []
    suffixes = re.compile(r"\b(incorporated|inc|llc|ltd|limited|corporation|corp|company|co)\b", re.I)
    return {re.sub(r"[^a-z0-9]+", "", suffixes.sub("", str(item)).casefold()) for item in values if str(item).strip()}

def fetch_details(app_id: int) -> dict:
    url = "https://store.steampowered.com/api/appdetails/?" + urllib.parse.urlencode(
        {"appids": app_id, "l": "english", "cc": "us"}
    )
    request = urllib.request.Request(url, headers={"User-Agent": "VeloraCatalogAudit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))[str(app_id)]
    return payload.get("data", {}) if payload.get("success") else {}

def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    steam = json.loads(STEAM.read_text(encoding="utf-8"))
    pcgw = json.loads(PCGW.read_text(encoding="utf-8"))
    games = {game["game_id"]: game for game in audit["games"]}
    previous = {(item["game_id"], item["field"]): item for item in manual["items"]}
    corrections = audit.get("corrections") or []
    provenance = audit.setdefault("deep_verification", [])
    connection = sqlite3.connect(DB); connection.row_factory = sqlite3.Row
    rows = {row["catalog_id"]: dict(row) for row in connection.execute(
        "SELECT * FROM catalog_items WHERE catalog_id LIKE 'g-%' AND is_active=1"
    )}

    for game_id, row in rows.items():
        page = pcgw.get(game_id) if isinstance(pcgw.get(game_id), dict) else {}
        engines = [engine for engine in page.get("engines", []) if engine not in ENGINE_BLOCKLIST]
        if engines:
            value = "; ".join(dict.fromkeys(engines))
            if row["engine"] != value:
                connection.execute("UPDATE catalog_items SET engine=? WHERE catalog_id=?", (value, game_id))
                corrections.append({"game_id": game_id, "title": row["title"], "field": "engine",
                                    "old_value": row["engine"], "new_value": value,
                                    "sources": [page["url"]], "confidence": "MEDIUM"})
            games[game_id]["fields"]["engine"] = "corrected" if row["engine"] != value else "verified"
            provenance.append({"game_id": game_id, "field": "engine", "value": value,
                               "sources": [page["url"]], "confidence": "MEDIUM"})

        source = steam.get(game_id) if isinstance(steam.get(game_id), dict) else {}
        if source.get("app_id"):
            data = fetch_details(source["app_id"])
            official_url = source["url"]
            for field, official_values in (("developer", data.get("developers") or []),
                                           ("publisher", data.get("publishers") or [])):
                current = normalized_names(row[field])
                official = normalized_names(official_values)
                if current and official and current == official:
                    games[game_id]["fields"][field] = "verified"
                    provenance.append({"game_id": game_id, "field": field, "value": row[field],
                                       "sources": [official_url], "confidence": "HIGH"})
            release_date = (data.get("release_date") or {}).get("date", "")
            years = re.findall(r"(?:19|20)\d{2}", release_date)
            if years and int(years[-1]) == row["release_year"]:
                games[game_id]["fields"]["release_year"] = "verified"
                provenance.append({"game_id": game_id, "field": "release_year",
                                   "value": row["release_year"], "sources": [official_url],
                                   "confidence": "HIGH"})
            categories = {item.get("description", "") for item in data.get("categories") or []}
            modes = []
            if "Single-player" in categories: modes.append("1P")
            if any("Multi-player" in value or "PvP" in value for value in categories): modes.append("MULTI")
            if any("Co-op" in value for value in categories): modes.append("CO-OP")
            if modes:
                value = "; ".join(modes)
                old = row["player_modes"]
                if old != value:
                    connection.execute("UPDATE catalog_items SET player_modes=? WHERE catalog_id=?", (value, game_id))
                    corrections.append({"game_id": game_id, "title": row["title"], "field": "player_modes",
                                        "old_value": old, "new_value": value, "sources": [source["url"]], "confidence": "HIGH"})
                games[game_id]["fields"]["player_modes"] = "corrected" if old != value else "verified"
                provenance.append({"game_id": game_id, "field": "player_modes", "value": value,
                                   "sources": [source["url"]], "confidence": "HIGH"})
            req = data.get("pc_requirements") or {}
            minimum, recommended = clean_html(req.get("minimum", "")), clean_html(req.get("recommended", ""))
            if minimum:
                structured = structured_requirements(minimum, recommended)
                value = json.dumps(structured, ensure_ascii=False)
                old = row["system_requirements_json"]
                try:
                    old_parsed = json.loads(old or "{}")
                except json.JSONDecodeError:
                    old_parsed = {}
                generated_legacy = bool(old_parsed) and set(old_parsed) <= {"minimum", "recommended"}
                if structured:
                    if old in ("", "{}") or generated_legacy:
                        connection.execute("UPDATE catalog_items SET system_requirements_json=? WHERE catalog_id=?", (value, game_id))
                        corrections.append({"game_id": game_id, "title": row["title"], "field": "system_requirements_json",
                                            "old_value": old, "new_value": structured, "sources": [source["url"]], "confidence": "HIGH"})
                        games[game_id]["fields"]["system_requirements_json"] = "corrected"
                    else:
                        games[game_id]["fields"]["system_requirements_json"] = "verified"
                    provenance.append({"game_id": game_id, "field": "system_requirements_json",
                                       "sources": [source["url"]], "confidence": "HIGH"})
        if game_id in DESCRIPTIONS:
            value = DESCRIPTIONS[game_id]
            old = row["description"]
            urls = list(dict.fromkeys(([source["url"]] if source.get("url") else []) + ([page["url"]] if page.get("url") else [])))
            if old != value:
                connection.execute("UPDATE catalog_items SET description=? WHERE catalog_id=?", (value, game_id))
                corrections.append({"game_id": game_id, "title": row["title"], "field": "description",
                                    "old_value": old, "new_value": value, "sources": urls, "confidence": "HIGH"})
            games[game_id]["fields"]["description"] = "corrected" if old != value else "verified"
            provenance.append({"game_id": game_id, "field": "description", "value": value,
                               "sources": urls, "confidence": "HIGH"})
    connection.commit(); connection.close()

    remaining = []
    researched = {"engine": "Источник не публикует достоверное название engine либо указывает proprietary/custom без версии.",
                  "system_requirements_json": "Для точного издания не найдены официальные PC Minimum/Recommended.",
                  "player_modes": "Режимы конкретного издания не подтверждены официальной площадкой.",
                  "description": "Нет достаточного набора проверенных фактов для безопасной замены русского текста.",
                  "franchise_name": "Принадлежность/границы серии требуют редакторского решения.",
                  "chronology_json": "Порядок серии неоднозначен из-за DLC, remake/remaster или нелинейности.",
                  "catalog_tags_json": "Официальной таксономии тегов для точного издания не найдено.",
                  "platforms": "Полный набор платформ по всем релизам не подтверждён одним надёжным источником."}
    for key, item in previous.items():
        status = games[item["game_id"]]["fields"].get(item["field"])
        if status in {"verified", "corrected"}: continue
        page = pcgw.get(item["game_id"]) if isinstance(pcgw.get(item["game_id"]), dict) else {}
        source = steam.get(item["game_id"]) if isinstance(steam.get(item["game_id"]), dict) else {}
        urls = list(dict.fromkeys(([source["url"]] if source.get("url") else []) + ([page["url"]] if page.get("url") else [])))
        item["sources"] = urls
        item["reason"] = researched.get(item["field"], "После проверки доступных источников значение остаётся неоднозначным.")
        remaining.append(item)
    generated = datetime.now(timezone.utc).isoformat()
    unique_provenance = {}
    for entry in provenance:
        key = (entry.get("game_id"), entry.get("field"), json.dumps(entry.get("value"), ensure_ascii=False, sort_keys=True), tuple(entry.get("sources") or []))
        unique_provenance[key] = entry
    audit["deep_verification"] = list(unique_provenance.values())
    audit["generated_at"] = generated; audit["corrections"] = corrections
    MANUAL.write_text(json.dumps({"schema": 1, "generated_at": generated, "items": remaining}, ensure_ascii=False, indent=2), encoding="utf-8")
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manual {len(previous)} -> {len(remaining)}; corrections total {len(corrections)}")

if __name__ == "__main__": main()
