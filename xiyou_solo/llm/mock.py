from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List

from xiyou_solo.llm.base import LLMCallResult


def _stable_actions(seed_text: str) -> List[str]:
    digest = hashlib.sha1(seed_text.encode("utf-8")).hexdigest()
    bank = [
        "Inspect nearby traces",
        "Ask a passerby",
        "Move cautiously forward",
        "Check for hidden signs",
        "Re-evaluate the clue",
    ]
    idx = int(digest[:2], 16) % len(bank)
    return [bank[idx], bank[(idx + 1) % len(bank)], bank[(idx + 2) % len(bank)]]


class MockProvider:
    def generate(self, dm_system: str, dm_context: str, player_input: str) -> LLMCallResult:
        del dm_system, dm_context
        started = time.perf_counter()
        lower = player_input.lower().strip()
        actions = _stable_actions(lower)

        need_check = any(k in lower for k in ("inspect", "check", "调查", "观察", "search"))
        enter_combat = any(k in lower for k in ("fight", "battle", "combat", "战斗", "开打"))
        pack_id = "bandits_1" if enter_combat else ""

        directive: Dict[str, Any] = {
            "need_check": need_check,
            "check": {"attribute": "Mind", "dc": 15 if need_check else 10, "reason": "Mock deterministic check."},
            "enter_combat": enter_combat,
            "combat": {"enemy_pack_id": pack_id},
            "grant_clue": need_check,
            "clue": {"title": "mock_clue", "detail": "A deterministic clue from MockProvider."} if need_check else {"title": "", "detail": ""},
            "flags_to_add": ["scene:mock_provider"],
            "world_tick": {"threat_delta": 0, "clock_delta": 1, "notes": "Mock world tick."},
            "npc_attitude_changes": [],
            "offer_actions": actions,
            "tone_tags": ["mock", "deterministic"],
        }
        narrative = (
            f"You act: {player_input.strip() or '(empty action)'}.\n"
            "The world responds in a stable, deterministic way for demo purposes."
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LLMCallResult(
            narrative=narrative,
            directive=directive,
            raw_text=narrative,
            latency_ms=latency_ms,
            tokens=64,
        )
