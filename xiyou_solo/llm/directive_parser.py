from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple


ALLOWED_ATTR: frozenset = frozenset({"Body", "Mind", "Spirit", "Luck"})
ALLOWED_DC: frozenset = frozenset({10, 15, 20, 25})

_DEFAULT_ATTR = "Luck"
_DEFAULT_DC = 15

DEFAULT_DIRECTIVE: Dict[str, Any] = {
    "need_check": False,
    "check": {"attribute": _DEFAULT_ATTR, "dc": _DEFAULT_DC, "reason": ""},
    "enter_combat": False,
    "combat": {"enemy_pack_id": ""},
    "grant_clue": False,
    "clue": {"title": "", "detail": ""},
    "flags_to_add": [],
    "world_tick": {"threat_delta": 0, "clock_delta": 1, "notes": ""},
    "npc_attitude_changes": [],
    "offer_actions": [],
    "tone_tags": [],
}


def _extract_json_blob(text: str) -> str:
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return ""


def _normalize_directive(raw: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(DEFAULT_DIRECTIVE)
    d["need_check"] = bool(raw.get("need_check", False))
    d["enter_combat"] = bool(raw.get("enter_combat", False))
    d["grant_clue"] = bool(raw.get("grant_clue", False))

    check = raw.get("check", {}) if isinstance(raw.get("check"), dict) else {}
    attr = str(check.get("attribute", _DEFAULT_ATTR))
    if attr not in ALLOWED_ATTR:
        attr = _DEFAULT_ATTR
    dc_raw = check.get("dc", _DEFAULT_DC)
    try:
        dc = int(dc_raw)
    except (TypeError, ValueError):
        dc = _DEFAULT_DC
    if dc not in ALLOWED_DC:
        dc = _DEFAULT_DC
    d["check"] = {"attribute": attr, "dc": dc, "reason": str(check.get("reason", ""))}

    combat = raw.get("combat", {}) if isinstance(raw.get("combat"), dict) else {}
    d["combat"] = {"enemy_pack_id": str(combat.get("enemy_pack_id", ""))}

    clue = raw.get("clue", {}) if isinstance(raw.get("clue"), dict) else {}
    d["clue"] = {"title": str(clue.get("title", "")), "detail": str(clue.get("detail", ""))}

    for key in ("flags_to_add", "npc_attitude_changes", "offer_actions", "tone_tags"):
        val = raw.get(key, [])
        d[key] = list(val) if isinstance(val, list) else []

    wt = raw.get("world_tick", {}) if isinstance(raw.get("world_tick"), dict) else {}
    try:
        threat_delta = int(wt.get("threat_delta", 0))
    except (TypeError, ValueError):
        threat_delta = 0
    try:
        clock_delta = int(wt.get("clock_delta", 1))
    except (TypeError, ValueError):
        clock_delta = 1
    d["world_tick"] = {"threat_delta": threat_delta, "clock_delta": clock_delta, "notes": str(wt.get("notes", ""))}
    return d


def parse_dm_output(text: str) -> Tuple[str, Dict[str, Any]]:
    blob = _extract_json_blob(text)
    if not blob:
        return text.strip(), dict(DEFAULT_DIRECTIVE)
    try:
        raw = json.loads(blob)
        directive = _normalize_directive(raw if isinstance(raw, dict) else {})
    except (json.JSONDecodeError, TypeError, ValueError):
        directive = dict(DEFAULT_DIRECTIVE)
    narrative = text.replace(blob, "")
    narrative = re.sub(r"```json|```", "", narrative, flags=re.IGNORECASE).strip()
    return narrative, directive
