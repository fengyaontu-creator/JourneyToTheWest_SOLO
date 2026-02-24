from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple


DEFAULT_DIRECTIVE: Dict[str, Any] = {
    "need_check": False,
    "check": {"attribute": "Mind", "dc": 10, "reason": ""},
    "enter_combat": False,
    "combat": {"enemy_pack_id": ""},
    "grant_clue": False,
    "clue": {"title": "", "detail": ""},
    "offer_actions": [],
    "tone_tags": [],
}

ALLOWED_ATTR = {"Body", "Mind", "Spirit", "Luck"}
ALLOWED_DC = {10, 15, 20, 25}


def _safe_bool(v: Any) -> bool:
    return bool(v)


def _extract_json_blob(text: str) -> str:
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1)
    # fallback: first {...} block
    m2 = re.search(r"(\{[\s\S]*\})", text)
    if m2:
        return m2.group(1)
    return ""


def _strip_json_from_narrative(text: str, blob: str) -> str:
    if not blob:
        return text.strip()
    cleaned = text.replace(blob, "")
    cleaned = re.sub(r"```json|```", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _normalize_directive(raw: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(DEFAULT_DIRECTIVE)
    d["need_check"] = _safe_bool(raw.get("need_check", False))
    d["enter_combat"] = _safe_bool(raw.get("enter_combat", False))
    d["grant_clue"] = _safe_bool(raw.get("grant_clue", False))

    check = raw.get("check", {}) if isinstance(raw.get("check", {}), dict) else {}
    attr = str(check.get("attribute", "Mind"))
    dc = int(check.get("dc", 10)) if str(check.get("dc", "")).isdigit() else 10
    if attr not in ALLOWED_ATTR:
        attr = "Mind"
    if dc not in ALLOWED_DC:
        dc = 10
    d["check"] = {"attribute": attr, "dc": dc, "reason": str(check.get("reason", ""))}

    combat = raw.get("combat", {}) if isinstance(raw.get("combat", {}), dict) else {}
    d["combat"] = {"enemy_pack_id": str(combat.get("enemy_pack_id", ""))}

    clue = raw.get("clue", {}) if isinstance(raw.get("clue", {}), dict) else {}
    d["clue"] = {"title": str(clue.get("title", "")), "detail": str(clue.get("detail", ""))}

    acts = raw.get("offer_actions", [])
    d["offer_actions"] = [str(x) for x in acts[:5]] if isinstance(acts, list) else []
    tags = raw.get("tone_tags", [])
    d["tone_tags"] = [str(x) for x in tags[:6]] if isinstance(tags, list) else []
    return d


def parse_dm_output(text: str) -> Tuple[str, Dict[str, Any]]:
    blob = _extract_json_blob(text)
    if not blob:
        return text.strip(), dict(DEFAULT_DIRECTIVE)
    try:
        obj = json.loads(blob)
        directive = _normalize_directive(obj if isinstance(obj, dict) else {})
    except (json.JSONDecodeError, ValueError, TypeError):
        directive = dict(DEFAULT_DIRECTIVE)
    narrative = _strip_json_from_narrative(text, blob)
    return narrative, directive

