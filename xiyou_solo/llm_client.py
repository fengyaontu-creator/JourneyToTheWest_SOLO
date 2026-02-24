from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

LAST_MODE = "unknown"
LAST_ERROR = ""


def _has_key() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY", "").strip())


def is_online_available() -> bool:
    return _has_key()


def _infer_lang(dm_context: str) -> str:
    m = re.search(r"language\s*[:=]\s*(zh|en)", dm_context, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return "zh"


def call_dm_stub(dm_system: str, dm_context: str, player_input: str) -> str:
    del dm_system
    lang = _infer_lang(dm_context)
    if lang == "en":
        narrative = (
            "You move forward through a lively post-pilgrimage land where clues and rumors mix.\n"
            "Locals react to your action and the situation sharpens around a single immediate thread.\n"
            "The scene remains light in tone, but your next move can still shift the pressure."
        )
        directive = {
            "need_check": True,
            "check": {"attribute": "Mind", "dc": 15, "reason": "You must verify fragmented leads under uncertainty."},
            "enter_combat": False,
            "combat": {"enemy_pack_id": ""},
            "grant_clue": False,
            "clue": {"title": "", "detail": ""},
            "offer_actions": ["Inspect details", "Talk to witnesses", "Push forward carefully"],
            "tone_tags": ["light", "myth"],
        }
    else:
        narrative = (
            "你继续推进，取经之后的天地依旧热闹，线索与传闻交错在一起。\n"
            "周围人对你的行动有了反应，局势也逐渐聚焦到一个关键点。\n"
            "整体氛围轻松，但你下一步仍会影响压力走向。"
        )
        directive = {
            "need_check": True,
            "check": {"attribute": "Mind", "dc": 15, "reason": "你需要在混杂线索中辨出关键真相。"},
            "enter_combat": False,
            "combat": {"enemy_pack_id": ""},
            "grant_clue": False,
            "clue": {"title": "", "detail": ""},
            "offer_actions": ["观察细节", "与目击者交谈", "谨慎推进"],
            "tone_tags": ["light", "myth"],
        }
    return f"{narrative}\n\n```json\n{json.dumps(directive, ensure_ascii=False, indent=2)}\n```"


def generate_dm_reply(dm_system: str, dm_context: str, player_input: str) -> str:
    global LAST_MODE, LAST_ERROR

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if not api_key:
        LAST_MODE = "offline_missing_key"
        LAST_ERROR = "missing_api_key"
        return call_dm_stub(dm_system, dm_context, player_input)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": dm_system},
            {"role": "user", "content": f"[Context]\n{dm_context}\n\n[Player Input]\n{player_input}"},
        ],
        "temperature": 0.8,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "xiyou_solo",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
        obj = json.loads(body)
        text = (
            obj.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not text:
            raise ValueError("empty_content")
        LAST_MODE = "online"
        LAST_ERROR = ""
        return text
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        LAST_MODE = "offline_error"
        LAST_ERROR = str(exc)
        return call_dm_stub(dm_system, dm_context, player_input)

