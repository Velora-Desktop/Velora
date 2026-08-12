"""Safe exact/alias resolution for locally bundled company logos."""
from __future__ import annotations

import re


_ALIASES = {
    "electronic arts": "company.electronic_arts",
    "electronic arts inc": "company.electronic_arts",
    "ea": "company.electronic_arts",
    "ea black box": "company.electronic_arts",
    "sony interactive entertainment": "company.sony_interactive_entertainment",
    "playstation pc llc": "company.sony_interactive_entertainment",
    "bethesda softworks": "company.bethesda_softworks",
    "xbox game studios": "company.xbox_game_studios",
    "microsoft studios": "company.xbox_game_studios",
    "microsoft game studios": "company.xbox_game_studios",
    "2k": "company.two_k_games",
    "2k games": "company.two_k_games",
    "blizzard entertainment": "company.blizzard_entertainment",
    "deep silver": "company.deep_silver",
    "capcom": "company.capcom",
    "capcom co ltd": "company.capcom",
    "warner bros games": "company.warner_bros_games",
    "rockstar games": "company.rockstar_games",
    "rockstar london": "company.rockstar_games",
    "rockstar vancouver": "company.rockstar_games",
    "rockstar toronto": "company.rockstar_games",
    "rockstar lincoln": "company.rockstar_games",
    "rockstar san diego": "company.rockstar_games",
    "ubisoft": "company.ubisoft",
    "cd projekt red": "company.cd_projekt_red",
    "cd projekt": "company.cd_projekt_red",
}


def normalize_company_name(name: str) -> str:
    value = name.casefold().strip()
    value = value.replace("&", " and ")
    return re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).strip()


def resolve_company_logo(name: str) -> str | None:
    """Return a semantic ID only for a reviewed exact/normalized alias."""
    return _ALIASES.get(normalize_company_name(name))


def split_company_names(value: str) -> list[str]:
    names: list[str] = []
    for part in value.split(";"):
        name = part.strip()
        if not name or name == "—" or re.fullmatch(r"Q\d+", name):
            continue
        names.append(name)
    return names
