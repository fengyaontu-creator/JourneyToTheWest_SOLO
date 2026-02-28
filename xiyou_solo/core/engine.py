from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from xiyou_solo.core import combat, rules
from xiyou_solo.core.state import GameState
from xiyou_solo.llm.base import LLMProvider


ATTR_MAP = {"Body": "body", "Mind": "wit", "Spirit": "spirit", "Luck": "luck"}


@dataclass
class TurnResult:
    narrative: str
    directive: Dict[str, Any]
    check_result: Optional[Dict[str, Any]]
    outcome: Optional[str]
    latency_ms: int
    tokens: Optional[int]


class GameEngine:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def build_context(self, state: GameState, log_data: Dict[str, Any], recent_n: int = 8) -> str:
        recent = log_data.get("events", [])[-recent_n:]
        lines = [
            f"language: {state.language}",
            f"session_id: {state.session_id}",
            f"mode: {getattr(state, 'mode', 'fast15')}",
            f"threat: {int(getattr(state, 'threat', 0))}/6",
            f"quest: {state.quest_title.get(state.language, state.quest_title.get('zh', ''))}",
            f"goal: {state.current_goal.get(state.language, state.current_goal.get('zh', ''))}",
            f"location: {state.location.get(state.language, state.location.get('zh', ''))}",
            f"turn: {state.turn}",
            f"progress: {state.progress}",
            f"threat_level: {state.threat_level}",
            f"hp: {state.hp}/{state.max_hp}",
            f"gold: {state.gold}",
            f"inventory: {state.inventory}",
            "recent_events:",
        ]
        for ev in recent:
            lines.append(f"- [{ev.get('type', 'unknown')}] {ev.get('content', '')}")
        return "\n".join(lines)

    def _apply_state_dict(self, state: GameState, payload: Dict[str, Any]) -> None:
        updated = GameState.from_dict(payload)
        state.__dict__.update(updated.__dict__)

    def _advance_fast15_threat(self, state: GameState) -> None:
        state.threat = max(0, int(getattr(state, "threat", 0)) + 1)
        if state.threat >= 6 and "finale" not in state.flags:
            state.flags.append("finale")

    def run_turn(self, state: GameState, log_data: Dict[str, Any], player_input: str, dm_system: str) -> TurnResult:
        log_data.setdefault("session_id", state.session_id)
        log_data.setdefault("events", [])

        state_dict = state.to_dict()
        if combat.is_combat_active(state_dict):
            action = combat.parse_combat_input(player_input)
            combat.apply_combat_action(state_dict, action)
            if not combat.is_combat_active(state_dict):
                combat.finalize_combat(state_dict)
            self._apply_state_dict(state, state_dict)
            self._advance_fast15_threat(state)

            text = combat.get_combat_prompt(state.to_dict())
            directive = {
                "need_check": False,
                "check": {"attribute": "Body", "dc": 10, "reason": "combat turn"},
                "enter_combat": combat.is_combat_active(state.to_dict()),
                "combat": {"enemy_pack_id": state.combat_state.get("enemy_pack_id", "") if isinstance(state.combat_state, dict) else ""},
                "grant_clue": False,
                "clue": {"title": "", "detail": ""},
                "flags_to_add": [],
                "world_tick": {"threat_delta": 0, "clock_delta": 1, "notes": "combat_turn"},
                "npc_attitude_changes": [],
                "offer_actions": ["attack", "skill <skill_id>", "use <item_id>", "defend", "flee"],
                "tone_tags": ["combat", "fast15"],
            }
            log_data["events"].append({"type": "combat_round", "content": player_input, "meta": {"action": action}})
            log_data["events"].append({"type": "dm_narrative", "content": text, "meta": {"directive": directive, "combat": True}})
            return TurnResult(narrative=text, directive=directive, check_result=None, outcome=None, latency_ms=0, tokens=None)

        state.turn += 1
        dm_context = self.build_context(state, log_data)
        llm_result = self.provider.generate(dm_system, dm_context, player_input)
        log_data["events"].append({"type": "action", "content": player_input, "meta": {}})
        directive = llm_result.directive if isinstance(llm_result.directive, dict) else {}

        check_result: Optional[Dict[str, Any]] = None
        outcome: Optional[str] = None
        if bool(directive.get("need_check", False)):
            check = directive.get("check", {}) if isinstance(directive.get("check"), dict) else {}
            attr = ATTR_MAP.get(str(check.get("attribute", "Mind")), "wit")
            dc = int(check.get("dc", 10))
            stat = int(state.stats.get(attr, 10))
            check_result = rules.resolve_check(stat=stat, dc=dc, bonus=0, mode="normal", use_passive=False)
            outcome = rules.outcome(int(check_result["total"]), dc)
            if outcome in {"outcome_critical", "outcome_success"}:
                state.progress += 1
            elif outcome in {"outcome_fail", "outcome_fumble"}:
                state.threat_level = min(9, state.threat_level + 1)

        if bool(directive.get("grant_clue", False)):
            clue = directive.get("clue", {}) if isinstance(directive.get("clue"), dict) else {}
            title = str(clue.get("title", "")).strip()
            if title:
                state.flags.append(f"clue:{title}")

        wt = directive.get("world_tick", {}) if isinstance(directive.get("world_tick"), dict) else {}
        threat_delta = int(wt.get("threat_delta", 0))
        state.threat_level = max(0, min(9, state.threat_level + threat_delta))

        if bool(directive.get("enter_combat", False)):
            c = directive.get("combat", {}) if isinstance(directive.get("combat"), dict) else {}
            enemy_pack_id = str(c.get("enemy_pack_id", "")).strip() or "bandits_1"
            state_dict = state.to_dict()
            combat.start_combat(state_dict, enemy_pack_id)
            self._apply_state_dict(state, state_dict)
            llm_result.narrative = f"{llm_result.narrative}\n\n{combat.get_combat_prompt(state_dict)}".strip()
            directive["offer_actions"] = ["attack", "skill <skill_id>", "use <item_id>", "defend", "flee"]

        self._advance_fast15_threat(state)

        log_data["events"].append(
            {
                "type": "dm_narrative",
                "content": llm_result.narrative,
                "meta": {"directive": directive, "latency_ms": llm_result.latency_ms, "tokens": llm_result.tokens},
            }
        )
        if check_result is not None:
            log_data["events"].append({"type": "roll_result", "content": "directive_check", "meta": check_result})

        return TurnResult(
            narrative=llm_result.narrative,
            directive=directive,
            check_result=check_result,
            outcome=outcome,
            latency_ms=llm_result.latency_ms,
            tokens=llm_result.tokens,
        )
