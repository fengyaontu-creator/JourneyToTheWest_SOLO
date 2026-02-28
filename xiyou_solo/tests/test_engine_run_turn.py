"""Tests for core/engine.py GameEngine.run_turn."""
from __future__ import annotations

import unittest
from typing import Any, Dict

from xiyou_solo.core.engine import GameEngine
from xiyou_solo.core.state import new_game_state
from xiyou_solo.llm.base import LLMCallResult
from xiyou_solo.llm.mock import MockProvider


class _SpyProvider:
    """Records every dm_context passed to generate()."""

    def __init__(self) -> None:
        self.contexts: list[str] = []
        self._delegate = MockProvider()

    def generate(self, dm_system: str, dm_context: str, player_input: str) -> LLMCallResult:
        self.contexts.append(dm_context)
        return self._delegate.generate(dm_system, dm_context, player_input)


def _fresh() -> tuple[GameEngine, Any, Dict[str, Any]]:
    state = new_game_state(session_id="test_sess", player_id="tester")
    log_data: Dict[str, Any] = {"session_id": "test_sess", "events": []}
    engine = GameEngine(provider=MockProvider())
    return engine, state, log_data


class TurnIncrementTests(unittest.TestCase):
    def test_turn_increments_by_one(self) -> None:
        engine, state, log_data = _fresh()
        self.assertEqual(state.turn, 0)
        engine.run_turn(state, log_data, "look around", "DM")
        self.assertEqual(state.turn, 1)
        engine.run_turn(state, log_data, "move forward", "DM")
        self.assertEqual(state.turn, 2)

    def test_result_fields_present(self) -> None:
        engine, state, log_data = _fresh()
        result = engine.run_turn(state, log_data, "walk west", "DM")
        self.assertIsInstance(result.narrative, str)
        self.assertIsInstance(result.directive, dict)
        self.assertIsInstance(result.latency_ms, int)


class ContextBuildRegressionTests(unittest.TestCase):
    """Regression: player input must NOT appear in recent_events when context is sent to LLM."""

    def test_current_action_absent_from_llm_context(self) -> None:
        spy = _SpyProvider()
        state = new_game_state(session_id="test_sess", player_id="tester")
        log_data: Dict[str, Any] = {"session_id": "test_sess", "events": []}
        engine = GameEngine(provider=spy)

        player_input = "inspect the altar stone"
        engine.run_turn(state, log_data, player_input, "DM")

        self.assertEqual(len(spy.contexts), 1)
        context = spy.contexts[0]
        # The current action must not be in the context sent to LLM
        self.assertNotIn(player_input, context,
                         "Player input must not appear in LLM context (would be sent twice).")

    def test_current_action_logged_after_llm_call(self) -> None:
        """The action IS written to log_data.events, just not visible to LLM for this turn."""
        spy = _SpyProvider()
        state = new_game_state(session_id="test_sess", player_id="tester")
        log_data: Dict[str, Any] = {"session_id": "test_sess", "events": []}
        engine = GameEngine(provider=spy)

        player_input = "open the chest"
        engine.run_turn(state, log_data, player_input, "DM")

        action_events = [e for e in log_data["events"] if e.get("type") == "action"]
        contents = [e.get("content") for e in action_events]
        self.assertIn(player_input, contents,
                      "Player input must be recorded in log_data.events after the turn.")

    def test_previous_action_visible_in_next_turn_context(self) -> None:
        """After turn N, the action from turn N is visible in the context of turn N+1."""
        spy = _SpyProvider()
        state = new_game_state(session_id="test_sess", player_id="tester")
        log_data: Dict[str, Any] = {"session_id": "test_sess", "events": []}
        engine = GameEngine(provider=spy)

        first_input = "examine the signpost"
        engine.run_turn(state, log_data, first_input, "DM")
        engine.run_turn(state, log_data, "walk north", "DM")

        # second call's context should contain the first action
        second_context = spy.contexts[1]
        self.assertIn(first_input, second_context,
                      "Previous turn's action should appear in the next turn's context.")


class CheckMechanicsTests(unittest.TestCase):
    def test_no_check_when_directive_false(self) -> None:
        engine, state, log_data = _fresh()
        # "walk west" does not trigger MockProvider's need_check keywords
        result = engine.run_turn(state, log_data, "walk west", "DM")
        self.assertIsNone(result.check_result)
        self.assertIsNone(result.outcome)

    def test_check_triggered_by_inspect_keyword(self) -> None:
        engine, state, log_data = _fresh()
        # MockProvider sets need_check=True for "inspect"
        result = engine.run_turn(state, log_data, "inspect the altar", "DM")
        self.assertIsNotNone(result.check_result)
        self.assertIn("total", result.check_result)
        self.assertIn(result.outcome, {
            "outcome_critical", "outcome_success", "outcome_partial",
            "outcome_fail", "outcome_fumble",
        })


if __name__ == "__main__":
    unittest.main()
