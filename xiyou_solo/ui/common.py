from __future__ import annotations

from pathlib import Path

from xiyou_solo.core.state import GameState


BASE_DIR = Path(__file__).resolve().parents[1]
DM_SYSTEM_PATH = BASE_DIR / "prompts" / "dm_system.txt"


def _read_dm_system() -> str:
    if DM_SYSTEM_PATH.exists():
        return DM_SYSTEM_PATH.read_text(encoding="utf-8")
    return "You are a light myth DM. Output Narrative plus Directive JSON."


def _summary(state: GameState) -> str:
    lang = state.language
    quest = state.quest_title.get(lang, state.quest_title.get("zh", ""))
    goal = state.current_goal.get(lang, state.current_goal.get("zh", ""))
    location = state.location.get(lang, state.location.get("zh", ""))
    short_threat = max(0, int(getattr(state, "threat", 0)))
    return (
        f"[session] {state.session_id}\n"
        f"Quest: {quest}\n"
        f"Goal: {goal}\n"
        f"Location: {location}\n"
        f"HP: {state.hp}/{state.max_hp}  Gold: {state.gold}\n"
        f"Progress: {state.progress}  Threat: {state.threat_level}\n"
        f"Threat: {short_threat}/6"
    )
