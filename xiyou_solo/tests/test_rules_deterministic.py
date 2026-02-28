from __future__ import annotations

from xiyou_solo.core import rules


def test_ability_mod_reference_values() -> None:
    assert rules.ability_mod(10) == 0
    assert rules.ability_mod(12) == 1
    assert rules.ability_mod(8) == -1


def test_roll_d20_adv_dis_are_deterministic_with_seed() -> None:
    rules.set_seed(2026)
    adv = rules.roll_d20("adv")
    assert adv["d20"] == max(adv["rolls"])

    rules.set_seed(2026)
    dis = rules.roll_d20("dis")
    assert dis["d20"] == min(dis["rolls"])

