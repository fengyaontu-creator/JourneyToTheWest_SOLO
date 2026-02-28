from __future__ import annotations

from typing import Any, Dict, Tuple

from xiyou_solo.core.engine import GameEngine
from xiyou_solo.core.state import GameState, new_game_state
from xiyou_solo.infra.session_store import GameSessionStore
from xiyou_solo.llm.openrouter import OpenRouterProvider
from xiyou_solo.ui.common import _read_dm_system, _summary

def create_bot_session(session_id: str, language: str = "zh", player_name: str = "tg_player") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    store = GameSessionStore()
    state = new_game_state(session_id=session_id, player_id=f"telegram:{player_name}", language=language)
    state.player_name = player_name
    log_data: Dict[str, Any] = {"session_id": session_id, "events": []}
    store.save_game(state, log_data)
    return state.to_dict(), log_data


def run_turn(session_id: str, player_input: str, api_key: str | None = None) -> Tuple[str, Dict[str, Any], str]:
    store = GameSessionStore()
    loaded = store.load_game(session_id)
    if not loaded:
        state_dict, log_data = create_bot_session(session_id, language="zh", player_name=f"tg_{session_id[-6:]}")
        state = GameState.from_dict(state_dict)
    else:
        state, log_data = loaded

    provider = OpenRouterProvider(api_key=api_key)
    engine = GameEngine(provider=provider)
    turn = engine.run_turn(state, log_data, player_input, _read_dm_system())
    store.save_game(state, log_data)
    return turn.narrative, turn.directive, _summary(state)


def run_utility_command(session_id: str, command: str) -> str:
    store = GameSessionStore()
    loaded = store.load_game(session_id)
    if not loaded:
        state_dict, log_data = create_bot_session(session_id, language="zh", player_name=f"tg_{session_id[-6:]}")
        state = GameState.from_dict(state_dict)
    else:
        state, log_data = loaded

    raw = (command or "").strip().lower()
    if raw == "status":
        return _summary(state)
    if raw == "lang" or raw.startswith("lang "):
        arg = raw.split(maxsplit=1)[1].strip() if " " in raw else ""
        if arg in {"zh", "en"}:
            state.language = arg
            store.save_game(state, log_data)
            return f"Language switched to {arg}"
        return f"Unknown language '{arg}'. Use: /lang zh  or  /lang en"
    if raw in {"inv", "shop"} or raw.startswith("buy") or raw.startswith("use"):
        return "This command is not enabled in runtime-lite mode."
    return "Unknown command. Use /help."
