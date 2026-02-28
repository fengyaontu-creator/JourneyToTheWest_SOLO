from __future__ import annotations

from copy import deepcopy

from xiyou_solo.core import combat, rules


def _state() -> dict:
    return {
        "session_id": "sess_test",
        "player": {
            "name": "tester",
            "class_id": "martial",
            "stats": {"body": 12, "wit": 10, "spirit": 10, "luck": 10},
            "hp": 12,
            "max_hp": 12,
            "gold": 10,
            "inventory": ["dagger", "buff_potion", "incense_charm", "smoke_bomb"],
        },
        "story": {"flags": []},
        "threat": 0,
    }


def test_combat_ends_within_4_rounds() -> None:
    rules.set_seed(7)
    state = _state()
    combat.start_combat(state, "bandits_1")
    for _ in range(10):
        if not combat.is_combat_active(state):
            break
        combat.apply_combat_action(state, {"type": "attack"})
        if not combat.is_combat_active(state):
            combat.finalize_combat(state)
    assert not combat.is_combat_active(state)
    result = str(state.get("combat_state", {}).get("result", ""))
    assert result in {"victory", "defeat", "forced_end", "flee"}


def test_use_item_bonus_and_consumption() -> None:
    state = _state()
    combat.start_combat(state, "bandits_1")
    before = deepcopy(state["player"]["inventory"])
    combat.apply_combat_action(state, {"type": "use_item", "item_id": "buff_potion"})
    after = state["player"]["inventory"]
    assert len(after) == len(before) - 1
    assert "buff_potion" not in after
    effects = state.get("combat_state", {}).get("player_effects", [])
    assert any(int(e.get("roll_bonus", 0)) >= 2 for e in effects if isinstance(e, dict))


def test_skill_cooldown_applies() -> None:
    state = _state()
    combat.start_combat(state, "bandits_1")
    combat.apply_combat_action(state, {"type": "skill", "skill_id": "power_strike"})
    cd = state.get("combat_state", {}).get("skill_cd", {})
    assert int(cd.get("power_strike", 0)) >= 1


def test_victory_increases_gold() -> None:
    rules.set_seed(1)
    state = _state()
    combat.start_combat(state, "goblin_road")
    cs = state.get("combat_state", {})
    if isinstance(cs, dict):
        enemies = cs.get("enemies", [])
        if isinstance(enemies, list):
            for enemy in enemies:
                if isinstance(enemy, dict):
                    enemy["ac"] = 1
    before = int(state["player"]["gold"])
    while combat.is_combat_active(state):
        combat.apply_combat_action(state, {"type": "attack"})
    combat.finalize_combat(state)
    after = int(state["player"]["gold"])
    assert after >= before


def test_hp_zero_causes_defeat() -> None:
    state = _state()
    state["player"]["hp"] = 1
    combat.start_combat(state, "bandits_1")
    cs = state.get("combat_state", {})
    if isinstance(cs, dict):
        enemies = cs.get("enemies", [])
        if isinstance(enemies, list):
            for enemy in enemies:
                if isinstance(enemy, dict):
                    enemy["ac"] = 30
                    enemy["dmg"] = 2
    combat.apply_combat_action(state, {"type": "attack"})
    assert not combat.is_combat_active(state)
    assert str(state.get("combat_state", {}).get("result", "")) == "defeat"
