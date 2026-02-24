from __future__ import annotations

from typing import Any, Dict, Iterable, List

from game_data import ATTR_LABEL, CLASSES, ITEMS, RACES
from i18n import t


def loc(node: Any, lang: str) -> str:
    if isinstance(node, dict):
        return node.get(lang) or node.get("zh") or ""
    return str(node)


def print_hud(state: Dict[str, Any]) -> None:
    lang = state.get("language", "zh")
    story = state["story"]
    player = state["player"]
    inv = player.get("inventory", [])
    key_items = ",".join(inv[:3]) if inv else "-"
    print(t("hud_line", lang, quest=loc(story["quest_title"], lang), goal=loc(story["current_goal"], lang), location=loc(story["location"], lang)))
    print(t("hud_line2", lang, hp=player["hp"], max_hp=player["max_hp"], gold=player["gold"], items=key_items))


def print_inventory(state: Dict[str, Any]) -> None:
    lang = state.get("language", "zh")
    p = state["player"]
    race_name = loc(RACES[p["race_id"]]["name"], lang)
    class_name = loc(CLASSES[p["class_id"]]["name"], lang)
    items = [f"{iid}({loc(ITEMS.get(iid, {}).get('name', {'zh': iid}), lang)})" for iid in p.get("inventory", [])]
    print(t("inventory_title", lang))
    print(f"{race_name} / {class_name}")
    print(f"HP {p['hp']}/{p['max_hp']}")
    print(t("inventory_gold", lang, gold=p["gold"]))
    print(t("inventory_items", lang, items=", ".join(items) if items else "-"))


def print_shop(state: Dict[str, Any]) -> None:
    lang = state.get("language", "zh")
    print(t("shop_title", lang))
    for iid, item in ITEMS.items():
        print(f"- {iid}: {loc(item['name'], lang)} | {item['price']}g | {loc(item['desc'], lang)}")


def print_choices(title: str, rows: Iterable[str]) -> None:
    print(title)
    for row in rows:
        print(row)


def parse_command(text: str) -> List[str]:
    return text.strip().split()

