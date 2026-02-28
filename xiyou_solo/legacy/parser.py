from __future__ import annotations

import json
import importlib.util
import re
from pathlib import Path
from typing import Any, Dict, Tuple


DEFAULT_DIRECTIVE: Dict[str, Any] = {
    "need_check": False,
    "check": {"attribute": "Mind", "dc": 10, "reason": ""},
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

ALLOWED_ATTR = {"Body", "Mind", "Spirit", "Luck"}
ALLOWED_DC = {10, 15, 20, 25}
ATTITUDE_SET = {"hostile", "unfriendly", "neutral", "friendly", "allied"}


def _builtin_fallback_directive() -> Dict[str, Any]:
    return {
        "need_check": False,
        "check": {"attribute": "Luck", "dc": 15, "reason": "fallback"},
        "enter_combat": False,
        "combat": {"enemy_pack_id": ""},
        "grant_clue": False,
        "clue": {"title": "", "detail": ""},
        "offer_actions": [],
        "tone_tags": [],
    }


def _builtin_validate_directive(directive: Dict[str, Any]) -> bool:
    if not isinstance(directive, dict):
        return False
    if "need_check" not in directive or "enter_combat" not in directive or "check" not in directive:
        return False
    if not isinstance(directive.get("need_check"), bool):
        return False
    if not isinstance(directive.get("enter_combat"), bool):
        return False
    check = directive.get("check")
    if not isinstance(check, dict):
        return False
    if check.get("attribute") not in ALLOWED_ATTR:
        return False
    if check.get("dc") not in ALLOWED_DC:
        return False
    return True


def _builtin_repair_directive(directive: Dict[str, Any]) -> Dict[str, Any]:
    base = _builtin_fallback_directive()
    if not isinstance(directive, dict):
        return base
    repaired = dict(directive)
    repaired["need_check"] = repaired.get("need_check", base["need_check"]) if isinstance(repaired.get("need_check"), bool) else base["need_check"]
    repaired["enter_combat"] = (
        repaired.get("enter_combat", base["enter_combat"]) if isinstance(repaired.get("enter_combat"), bool) else base["enter_combat"]
    )
    check = repaired.get("check") if isinstance(repaired.get("check"), dict) else {}
    attr = check.get("attribute", base["check"]["attribute"])
    dc = check.get("dc", base["check"]["dc"])
    reason = check.get("reason", base["check"]["reason"])
    if attr not in ALLOWED_ATTR:
        attr = base["check"]["attribute"]
    if dc not in ALLOWED_DC:
        dc = base["check"]["dc"]
    repaired["check"] = {"attribute": attr, "dc": dc, "reason": reason if isinstance(reason, str) else base["check"]["reason"]}
    return repaired


def _builtin_sanitize_directive(directive: Dict[str, Any]) -> Dict[str, Any]:
    base = _builtin_fallback_directive()
    allowed = {"need_check", "check", "enter_combat", "combat", "grant_clue", "clue", "offer_actions", "tone_tags"}
    raw = directive if isinstance(directive, dict) else {}
    out = {k: raw[k] for k in allowed if k in raw}
    out["need_check"] = out.get("need_check", base["need_check"]) if isinstance(out.get("need_check"), bool) else base["need_check"]
    out["enter_combat"] = out.get("enter_combat", base["enter_combat"]) if isinstance(out.get("enter_combat"), bool) else base["enter_combat"]
    out["grant_clue"] = out.get("grant_clue", base["grant_clue"]) if isinstance(out.get("grant_clue"), bool) else base["grant_clue"]
    check = out.get("check", {})
    if not isinstance(check, dict):
        check = {}
    attr = check.get("attribute", base["check"]["attribute"])
    dc = check.get("dc", base["check"]["dc"])
    if attr not in ALLOWED_ATTR:
        attr = base["check"]["attribute"]
    if dc not in ALLOWED_DC:
        dc = base["check"]["dc"]
    reason = check.get("reason", base["check"]["reason"])
    out["check"] = {"attribute": attr, "dc": dc, "reason": reason if isinstance(reason, str) else base["check"]["reason"]}
    combat = out.get("combat", {})
    if not isinstance(combat, dict):
        combat = {}
    enemy_pack_id = combat.get("enemy_pack_id", "")
    if not isinstance(enemy_pack_id, str):
        enemy_pack_id = str(enemy_pack_id)
    if not out["enter_combat"]:
        enemy_pack_id = ""
    out["combat"] = {"enemy_pack_id": enemy_pack_id}
    clue = out.get("clue", {})
    if not isinstance(clue, dict):
        clue = {}
    out["clue"] = {
        "title": clue.get("title", "") if isinstance(clue.get("title", ""), str) else "",
        "detail": clue.get("detail", "") if isinstance(clue.get("detail", ""), str) else "",
    }
    acts = out.get("offer_actions", [])
    out["offer_actions"] = [str(x) for x in acts] if isinstance(acts, list) else []
    tags = out.get("tone_tags", [])
    out["tone_tags"] = [str(x) for x in tags] if isinstance(tags, list) else []
    return out


def _load_validator_functions():
    try:
        validator_path = Path(__file__).resolve().parent / "engine" / "validator.py"
        spec = importlib.util.spec_from_file_location("directive_validator", validator_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load validator module from: {validator_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.validate_directive, module.repair_directive, module.fallback_directive
    except Exception as exc:
        print(f"[warn] validator missing, using builtin fallback: {exc}")
        return _builtin_validate_directive, _builtin_repair_directive, _builtin_fallback_directive


_validate_directive, _repair_directive, _fallback_directive = _load_validator_functions()


def _load_guardrail_functions():
    try:
        guardrail_path = Path(__file__).resolve().parent / "engine" / "guardrail.py"
        spec = importlib.util.spec_from_file_location("directive_guardrail", guardrail_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load guardrail module from: {guardrail_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.sanitize_directive
    except Exception as exc:
        print(f"[warn] guardrail missing, using builtin fallback: {exc}")
        return _builtin_sanitize_directive


_sanitize_directive = _load_guardrail_functions()


def _safe_bool(v: Any) -> bool:
    return bool(v)


def _extract_json_blob(text: str) -> str:
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1)

    marker = re.search(r"(part\s*b|directive\s*json)", text, re.IGNORECASE)
    search_space = text[marker.end() :] if marker else text

    blob = extract_first_balanced_json(search_space)
    if blob:
        return blob
    if marker:
        blob = extract_first_balanced_json(text)
        if blob:
            return blob
    return ""


def extract_first_balanced_json(s: str) -> str:
    i = 0
    n = len(s)
    while i < n:
        start = s.find("{", i)
        if start < 0:
            return ""
        depth = 0
        in_string = False
        escape = False
        j = start
        while j < n:
            ch = s[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = s[start : j + 1]
                        try:
                            obj = json.loads(candidate)
                        except (json.JSONDecodeError, TypeError, ValueError):
                            i = start + 1
                            break
                        if isinstance(obj, dict):
                            return candidate
                        i = start + 1
                        break
                    if depth < 0:
                        i = start + 1
                        break
            j += 1
        else:
            return ""
        if j >= n:
            return ""
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

    flags = raw.get("flags_to_add", [])
    if isinstance(flags, list):
        d["flags_to_add"] = [str(x).strip() for x in flags[:8] if str(x).strip()]
    else:
        d["flags_to_add"] = []

    wt = raw.get("world_tick", {}) if isinstance(raw.get("world_tick", {}), dict) else {}
    threat_delta = wt.get("threat_delta", 0)
    clock_delta = wt.get("clock_delta", 1)
    try:
        threat_delta = int(threat_delta)
    except (TypeError, ValueError):
        threat_delta = 0
    try:
        clock_delta = int(clock_delta)
    except (TypeError, ValueError):
        clock_delta = 1
    d["world_tick"] = {
        "threat_delta": max(-2, min(3, threat_delta)),
        "clock_delta": max(1, min(6, clock_delta)),
        "notes": str(wt.get("notes", ""))[:160],
    }

    npc_changes: Any = raw.get("npc_attitude_changes", [])
    norm_changes = []
    if isinstance(npc_changes, list):
        for row in npc_changes[:5]:
            if not isinstance(row, dict):
                continue
            npc_id = str(row.get("npc_id", "")).strip()
            if not npc_id:
                continue
            name = str(row.get("name", "")).strip()
            reason = str(row.get("reason", "")).strip()
            delta_raw = row.get("delta", 0)
            try:
                delta = int(delta_raw)
            except (TypeError, ValueError):
                delta = 0
            set_to = str(row.get("set_to", "")).strip().lower()
            if set_to not in ATTITUDE_SET:
                set_to = ""
            norm_changes.append(
                {
                    "npc_id": npc_id,
                    "name": name,
                    "delta": max(-2, min(2, delta)),
                    "set_to": set_to,
                    "reason": reason[:160],
                }
            )
    d["npc_attitude_changes"] = norm_changes

    acts = raw.get("offer_actions", [])
    d["offer_actions"] = [str(x) for x in acts[:5]] if isinstance(acts, list) else []
    tags = raw.get("tone_tags", [])
    d["tone_tags"] = [str(x) for x in tags[:6]] if isinstance(tags, list) else []
    return d


def parse_dm_output(text: str) -> Tuple[str, Dict[str, Any]]:
    blob = _extract_json_blob(text)
    if not blob:
        base = dict(DEFAULT_DIRECTIVE)
        core = _sanitize_directive(_fallback_directive())
        base["need_check"] = core["need_check"]
        base["check"] = core["check"]
        base["enter_combat"] = core["enter_combat"]
        base["combat"] = core.get("combat", {"enemy_pack_id": ""})
        base["grant_clue"] = core.get("grant_clue", False)
        base["clue"] = core.get("clue", {"title": "", "detail": ""})
        base["offer_actions"] = core.get("offer_actions", [])
        base["tone_tags"] = core.get("tone_tags", [])
        return text.strip(), base

    raw_obj: Dict[str, Any] = {}
    core_directive: Dict[str, Any]
    try:
        obj = json.loads(blob)
        raw_obj = obj if isinstance(obj, dict) else {}
        repaired = _repair_directive(raw_obj)
        core_directive = repaired if _validate_directive(repaired) else _fallback_directive()
    except (json.JSONDecodeError, ValueError, TypeError):
        core_directive = _fallback_directive()

    core_directive = _sanitize_directive(core_directive)
    directive = _normalize_directive(core_directive)
    directive["need_check"] = core_directive["need_check"]
    directive["check"] = core_directive["check"]
    directive["enter_combat"] = core_directive["enter_combat"]
    directive["combat"] = core_directive.get("combat", {"enemy_pack_id": ""})
    directive["grant_clue"] = core_directive.get("grant_clue", False)
    directive["clue"] = core_directive.get("clue", {"title": "", "detail": ""})
    directive["offer_actions"] = core_directive.get("offer_actions", [])
    directive["tone_tags"] = core_directive.get("tone_tags", [])
    narrative = _strip_json_from_narrative(text, blob)
    return narrative, directive
