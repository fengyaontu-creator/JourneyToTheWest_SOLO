from __future__ import annotations

import argparse
from typing import Any, Dict, Tuple

from xiyou_solo.core.engine import GameEngine
from xiyou_solo.core.state import GameState, new_game_state
from xiyou_solo.infra.config import AppConfig
from xiyou_solo.infra.metrics import MetricsCollector, format_metric_line
from xiyou_solo.infra.session_store import GameSessionStore
from xiyou_solo.llm.base import LLMProvider
from xiyou_solo.llm.mock import MockProvider
from xiyou_solo.llm.openrouter import OpenRouterProvider
from xiyou_solo.ui.common import _read_dm_system, _summary


QUIT_WORDS = {"quit", "exit", "q", "/quit"}


def _provider_from_name(name: str) -> LLMProvider:
    if name == "openrouter":
        return OpenRouterProvider()
    return MockProvider()


def _init_new_session(store: GameSessionStore, player_id: str, language: str = "zh") -> Tuple[GameState, Dict[str, Any]]:
    sid = store.create_session(
        player_id=player_id,
        meta={"source": "cli_refactor", "language": language, "created_by": "ui.cli"},
    )
    state = new_game_state(session_id=sid, player_id=player_id, language=language)
    log_data: Dict[str, Any] = {"session_id": sid, "events": []}
    store.save_game(state, log_data)
    store.set_active_session(sid)
    return state, log_data


def _load_or_create_initial_state(store: GameSessionStore, player_id: str, session_arg: str | None) -> Tuple[GameState, Dict[str, Any]]:
    if session_arg:
        loaded = store.load_game(session_arg)
        if loaded:
            store.set_active_session(session_arg)
            return loaded
        return _init_new_session(store, player_id=player_id)

    active_sid = store.get_active_session()
    if active_sid:
        loaded = store.load_game(active_sid)
        if loaded:
            return loaded
    return _init_new_session(store, player_id=player_id)


def _handle_session_command(
    raw: str,
    store: GameSessionStore,
    player_id: str,
    state: GameState,
    log_data: Dict[str, Any],
) -> Tuple[bool, GameState, Dict[str, Any]]:
    if raw == "/new":
        new_state, new_log = _init_new_session(store, player_id=player_id, language=state.language)
        print(f"[session] switched to {new_state.session_id}")
        return True, new_state, new_log

    if raw == "/list":
        rows = store.list_sessions(player_id=player_id)
        if not rows:
            print("No sessions.")
            return True, state, log_data
        print("Sessions:")
        for row in rows:
            sid = row.get("session_id", "")
            meta = row.get("meta", {}) if isinstance(row.get("meta"), dict) else {}
            print(f"- {sid}  created_at={meta.get('created_at', '')}")
        return True, state, log_data

    if raw.startswith("/load "):
        sid = raw.split(maxsplit=1)[1].strip()
        rows = {r.get("session_id", "") for r in store.list_sessions(player_id=player_id)}
        if sid not in rows:
            print("Session not found for current player.")
            return True, state, log_data
        loaded = store.load_game(sid)
        if not loaded:
            print("Session files missing.")
            return True, state, log_data
        loaded_state, loaded_log = loaded
        store.set_active_session(sid)
        print(f"[session] switched to {sid}")
        return True, loaded_state, loaded_log

    return False, state, log_data


def run_cli(provider_name: str, session_arg: str | None) -> None:
    _ = AppConfig.from_env(provider=provider_name)
    store = GameSessionStore()
    player_id = store.get_or_create_player_id()

    migrated_sid = store.migrate_legacy_shared(player_id=player_id)
    if migrated_sid:
        store.set_active_session(migrated_sid)

    provider = _provider_from_name(provider_name)
    engine = GameEngine(provider=provider)
    metrics = MetricsCollector()
    dm_system = _read_dm_system()

    state, log_data = _load_or_create_initial_state(store, player_id=player_id, session_arg=session_arg)

    print("xiyou_solo CLI (refactor demo)")
    print(f"provider={provider_name} player_id={player_id}")
    print("commands: /new, /list, /load <session_id>, /quit")

    while True:
        print(_summary(state))
        raw = input("> ").strip()
        if not raw:
            continue
        if raw.lower() in QUIT_WORDS:
            store.save_game(state, log_data)
            print("Bye.")
            return

        handled, state, log_data = _handle_session_command(raw, store, player_id, state, log_data)
        if handled:
            continue

        turn = engine.run_turn(state, log_data, raw, dm_system)
        metric = metrics.record(latency_ms=turn.latency_ms, tokens=turn.tokens)
        store.save_game(state, log_data)

        print(f"[DM] {turn.narrative}")
        if turn.outcome:
            print(f"[rule] outcome={turn.outcome}")
        actions = turn.directive.get("offer_actions", [])
        if isinstance(actions, list) and actions:
            print("Actions:")
            for idx, action in enumerate(actions[:4], start=1):
                print(f"{idx}. {action}")
        print(format_metric_line(metric.latency_ms, metric.tokens))


def main() -> None:
    parser = argparse.ArgumentParser(description="xiyou_solo demo CLI")
    parser.add_argument("--provider", choices=["openrouter", "mock"], default="mock")
    parser.add_argument("--session", default=None, help="Optional session_id; if omitted, use active session.")
    args = parser.parse_args()
    run_cli(provider_name=args.provider, session_arg=args.session)


if __name__ == "__main__":
    main()
