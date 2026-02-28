from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from xiyou_solo.llm.base import LLMCallResult
from xiyou_solo.llm.directive_parser import parse_dm_output


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def _infer_lang(dm_context: str) -> str:
    m = re.search(r"language\s*[:=]\s*(zh|en)", dm_context, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return "zh"


def _stub_reply(dm_context: str) -> str:
    lang = _infer_lang(dm_context)
    if lang == "en":
        narrative = "You move forward and uncover a useful clue as the scene shifts."
        directive = {
            "need_check": True,
            "check": {"attribute": "Mind", "dc": 15, "reason": "Follow scattered clues."},
            "enter_combat": False,
            "combat": {"enemy_pack_id": ""},
            "grant_clue": True,
            "clue": {"title": "stub_clue", "detail": "A stable offline clue."},
            "flags_to_add": ["scene:offline_stub"],
            "world_tick": {"threat_delta": 0, "clock_delta": 1, "notes": "Offline mode"},
            "npc_attitude_changes": [],
            "offer_actions": ["Inspect details", "Talk to locals", "Move carefully"],
            "tone_tags": ["light", "myth"],
        }
    else:
        narrative = "你继续前进，场景有了新线索，局势逐渐清晰。"
        directive = {
            "need_check": True,
            "check": {"attribute": "Mind", "dc": 15, "reason": "辨别混杂线索。"},
            "enter_combat": False,
            "combat": {"enemy_pack_id": ""},
            "grant_clue": True,
            "clue": {"title": "stub_clue", "detail": "离线模式下的稳定线索。"},
            "flags_to_add": ["scene:offline_stub"],
            "world_tick": {"threat_delta": 0, "clock_delta": 1, "notes": "offline mode"},
            "npc_attitude_changes": [],
            "offer_actions": ["观察细节", "与路人交谈", "谨慎推进"],
            "tone_tags": ["light", "myth"],
        }
    return f"{narrative}\n\n```json\n{json.dumps(directive, ensure_ascii=False, indent=2)}\n```"


def _error_reply(lang: str, kind: str) -> str:
    if lang == "en":
        if kind == "missing_key":
            narrative = "OpenRouter API key is missing. Please provide a valid key."
            actions = ["Check your API key", "Set OPENROUTER_API_KEY", "Retry after setup"]
        elif kind == "invalid_key":
            narrative = "OpenRouter key is invalid or unauthorized (401/403). Please update your key."
            actions = ["Re-enter API key", "Check key permissions", "Retry request"]
        elif kind == "quota":
            narrative = "OpenRouter quota/rate limit reached (402/429). Please top up or wait before retrying."
            actions = ["Check quota usage", "Wait and retry", "Use another key"]
        elif kind == "network":
            narrative = "OpenRouter request failed due to network/timeout. Please retry later."
            actions = ["Retry request", "Check network", "Try again later"]
        else:
            narrative = "OpenRouter request failed. Please retry later."
            actions = ["Retry request", "Check API status", "Try again later"]
    else:
        if kind == "missing_key":
            narrative = "未检测到 OpenRouter API key，请先提供有效 key。"
            actions = ["检查 API key", "设置 OPENROUTER_API_KEY", "设置后重试"]
        elif kind == "invalid_key":
            narrative = "OpenRouter key 无效或无权限（401/403），请更换 key。"
            actions = ["重新输入 API key", "检查 key 权限", "重新尝试"]
        elif kind == "quota":
            narrative = "OpenRouter 配额或速率限制已触发（402/429），请充值/等待后重试。"
            actions = ["查看配额使用", "等待后重试", "更换 key"]
        elif kind == "network":
            narrative = "OpenRouter 请求失败（网络/超时），请稍后重试。"
            actions = ["重试请求", "检查网络", "稍后再试"]
        else:
            narrative = "OpenRouter 请求失败，请稍后重试。"
            actions = ["重试请求", "检查服务状态", "稍后再试"]

    directive = {
        "need_check": False,
        "check": {"attribute": "Mind", "dc": 10, "reason": "Provider error."},
        "enter_combat": False,
        "combat": {"enemy_pack_id": ""},
        "grant_clue": False,
        "clue": {"title": "", "detail": ""},
        "flags_to_add": ["provider:error"],
        "world_tick": {"threat_delta": 0, "clock_delta": 0, "notes": "provider_error"},
        "npc_attitude_changes": [],
        "offer_actions": actions,
        "tone_tags": ["system", "error"],
    }
    return f"{narrative}\n\n```json\n{json.dumps(directive, ensure_ascii=False, indent=2)}\n```"


class OpenRouterProvider:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or "").strip() or None
        self.model = (model or "").strip() or None

    def generate(self, dm_system: str, dm_context: str, player_input: str) -> LLMCallResult:
        started = time.perf_counter()
        lang = _infer_lang(dm_context)
        api_key = self.api_key if self.api_key is not None else os.getenv("OPENROUTER_API_KEY", "").strip()
        model = self.model if self.model is not None else os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        raw_text = ""
        token_usage = None

        if not api_key:
            raw_text = _error_reply(lang, "missing_key")
        else:
            payload: Dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": dm_system},
                    {"role": "user", "content": f"[Context]\n{dm_context}\n\n[Player Input]\n{player_input}"},
                ],
                "temperature": 0.8,
            }
            req = urllib.request.Request(
                OPENROUTER_URL,
                data=json.dumps(payload).encode("utf-8"),
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
                raw_text = obj.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                usage = obj.get("usage", {}) if isinstance(obj.get("usage"), dict) else {}
                total_tokens = usage.get("total_tokens")
                if isinstance(total_tokens, int):
                    token_usage = total_tokens
                if not raw_text:
                    raw_text = _error_reply(lang, "other")
            except urllib.error.HTTPError as exc:
                if exc.code in {401, 403}:
                    raw_text = _error_reply(lang, "invalid_key")
                elif exc.code in {402, 429}:
                    raw_text = _error_reply(lang, "quota")
                else:
                    raw_text = _error_reply(lang, "other")
            except (urllib.error.URLError, TimeoutError):
                raw_text = _error_reply(lang, "network")
            except (ValueError, json.JSONDecodeError):
                raw_text = _error_reply(lang, "other")

        narrative, directive = parse_dm_output(raw_text)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LLMCallResult(
            narrative=narrative,
            directive=directive,
            raw_text=raw_text,
            latency_ms=latency_ms,
            tokens=token_usage,
        )
