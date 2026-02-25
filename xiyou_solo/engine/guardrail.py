from __future__ import annotations

import logging
from typing import Any, Dict


_ALLOWED_TOP_LEVEL = {
    "need_check",
    "check",
    "enter_combat",
    "combat",
    "grant_clue",
    "clue",
    "offer_actions",
    "tone_tags",
}

_ALLOWED_ATTRIBUTES = {"Body", "Mind", "Spirit", "Luck"}
_ALLOWED_DC = {10, 15, 20, 25}

_POLLUTION_KEYS = {
    "gold",
    "gold_change",
    "hp",
    "hp_change",
    "inventory",
    "inventory_change",
    "state",
    "state_update",
}

_LOGGER = logging.getLogger(__name__)


def _is_pollution_key(key: str) -> bool:
    lowered = key.strip().lower()
    if lowered in _POLLUTION_KEYS:
        return True
    return any(token in lowered for token in ("gold", "hp", "inventory", "state"))


def _strip_pollution(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if _is_pollution_key(key):
                _LOGGER.warning("Directive pollution key dropped: %s", key)
                continue
            cleaned[key] = _strip_pollution(v)
        return cleaned
    if isinstance(value, list):
        return [_strip_pollution(x) for x in value]
    return value


def sanitize_directive(directive: Dict[str, Any]) -> Dict[str, Any]:
    raw = directive if isinstance(directive, dict) else {}
    raw = _strip_pollution(raw)

    sanitized: Dict[str, Any] = {}
    for key in _ALLOWED_TOP_LEVEL:
        if key in raw:
            sanitized[key] = raw[key]

    sanitized["need_check"] = sanitized.get("need_check", False) if isinstance(sanitized.get("need_check"), bool) else False
    sanitized["enter_combat"] = sanitized.get("enter_combat", False) if isinstance(sanitized.get("enter_combat"), bool) else False
    sanitized["grant_clue"] = sanitized.get("grant_clue", False) if isinstance(sanitized.get("grant_clue"), bool) else False

    check = sanitized.get("check", {})
    if not isinstance(check, dict):
        check = {}
    attribute = check.get("attribute", "Luck")
    if attribute not in _ALLOWED_ATTRIBUTES:
        attribute = "Luck"
    dc = check.get("dc", 15)
    if not isinstance(dc, int) or dc not in _ALLOWED_DC:
        dc = 15
    reason = check.get("reason", "fallback")
    sanitized["check"] = {
        "attribute": attribute,
        "dc": dc,
        "reason": reason if isinstance(reason, str) else "fallback",
    }

    combat = sanitized.get("combat", {})
    if not isinstance(combat, dict):
        combat = {}
    enemy_pack_id = combat.get("enemy_pack_id", "")
    enemy_pack_id = enemy_pack_id if isinstance(enemy_pack_id, str) else str(enemy_pack_id)
    if not sanitized["enter_combat"]:
        enemy_pack_id = ""
    sanitized["combat"] = {"enemy_pack_id": enemy_pack_id}

    clue = sanitized.get("clue", {})
    if not isinstance(clue, dict):
        clue = {}
    sanitized["clue"] = {
        "title": clue.get("title", "") if isinstance(clue.get("title", ""), str) else "",
        "detail": clue.get("detail", "") if isinstance(clue.get("detail", ""), str) else "",
    }

    acts = sanitized.get("offer_actions", [])
    sanitized["offer_actions"] = [str(x) for x in acts[:5]] if isinstance(acts, list) else []

    tags = sanitized.get("tone_tags", [])
    sanitized["tone_tags"] = [str(x) for x in tags[:6]] if isinstance(tags, list) else []

    return sanitized
