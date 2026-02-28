from __future__ import annotations

from xiyou_solo.core.state import GameState


def test_state_serialization() -> None:
    src = GameState(
        session_id="sess_test_001",
        player_id="player_abc",
        language="en",
        player_name="demo",
        stats={"body": 12, "wit": 14, "spirit": 10, "luck": 9},
        hp=11,
        max_hp=15,
        gold=99,
        inventory=["healing_herbs", "dagger"],
        turn=3,
        progress=2,
        threat_level=4,
        flags=["clue:map"],
    )
    dumped = src.to_dict()
    restored = GameState.from_dict(dumped)

    assert restored.session_id == src.session_id
    assert restored.player_id == src.player_id
    assert restored.language == src.language
    assert restored.stats == src.stats
    assert restored.hp == src.hp
    assert restored.max_hp == src.max_hp
    assert restored.gold == src.gold
    assert restored.inventory == src.inventory
    assert restored.turn == src.turn
    assert restored.progress == src.progress
    assert restored.threat_level == src.threat_level
    assert restored.flags == src.flags

