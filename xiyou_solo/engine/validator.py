from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


_BASE_DIR = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _BASE_DIR / "schemas" / "directive_schema.json"

_DEFAULT_ATTRIBUTE = "Luck"
_DEFAULT_DC = 15
_DEFAULT_REASON = "fallback"
_ALLOWED_ATTRIBUTES = {"Body", "Mind", "Spirit", "Luck"}
_ALLOWED_DC = {10, 15, 20, 25}


def _load_schema() -> Dict[str, Any]:
    try:
        return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "required": ["need_check", "check", "enter_combat"],
            "properties": {"check": {"required": ["attribute", "dc", "reason"]}},
        }


_SCHEMA = _load_schema()
_REQUIRED_TOP = set(_SCHEMA.get("required", []))
_REQUIRED_CHECK = set(_SCHEMA.get("properties", {}).get("check", {}).get("required", []))


def _repair_bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def fallback_directive() -> Dict[str, Any]:
    return {
        "need_check": False,
        "check": {
            "attribute": _DEFAULT_ATTRIBUTE,
            "dc": _DEFAULT_DC,
            "reason": _DEFAULT_REASON,
        },
        "enter_combat": False,
    }


def validate_directive(directive: Dict[str, Any]) -> bool:
    if not isinstance(directive, dict):
        return False

    if not _REQUIRED_TOP.issubset(directive.keys()):
        return False

    if not isinstance(directive.get("need_check"), bool):
        return False
    if not isinstance(directive.get("enter_combat"), bool):
        return False

    check = directive.get("check")
    if not isinstance(check, dict):
        return False
    if not _REQUIRED_CHECK.issubset(check.keys()):
        return False

    attribute = check.get("attribute")
    dc = check.get("dc")
    reason = check.get("reason")

    if attribute not in _ALLOWED_ATTRIBUTES:
        return False
    if dc not in _ALLOWED_DC or not isinstance(dc, int):
        return False
    if not isinstance(reason, str):
        return False

    return True


def repair_directive(directive: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(directive, dict):
        return fallback_directive()

    repaired: Dict[str, Any] = dict(directive)
    repaired["need_check"] = _repair_bool(repaired.get("need_check", False), False)
    repaired["enter_combat"] = _repair_bool(repaired.get("enter_combat", False), False)

    check_raw = repaired.get("check")
    if not isinstance(check_raw, dict) or not _REQUIRED_CHECK.issubset(check_raw.keys()):
        repaired["check"] = {
            "attribute": _DEFAULT_ATTRIBUTE,
            "dc": _DEFAULT_DC,
            "reason": _DEFAULT_REASON,
        }
    else:
        check = dict(check_raw)
        if check.get("attribute") not in _ALLOWED_ATTRIBUTES:
            check["attribute"] = _DEFAULT_ATTRIBUTE

        dc = check.get("dc")
        if not isinstance(dc, int) or dc not in _ALLOWED_DC:
            check["dc"] = _DEFAULT_DC

        reason = check.get("reason")
        check["reason"] = reason if isinstance(reason, str) else _DEFAULT_REASON

        repaired["check"] = check

    return repaired
