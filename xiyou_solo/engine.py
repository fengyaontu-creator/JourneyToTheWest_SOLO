"""Compatibility shim – exposes core engine and rules under xiyou_solo.engine.

Existing tests and scripts may use::

    from xiyou_solo import engine
    engine.set_seed(42)
    engine.resolve_check(...)

New code should import from ``xiyou_solo.core`` directly.
"""
from xiyou_solo.core.engine import GameEngine as Engine
from xiyou_solo.core.rules import (
    ability_mod,
    gen_stat_3d6,
    gen_stat_4d6_drop_lowest,
    generate_stats,
    outcome,
    passive,
    resolve_check,
    roll_d20,
    roll_d6,
    roll_dice,
    set_seed,
)

__all__ = [
    "Engine",
    "ability_mod",
    "gen_stat_3d6",
    "gen_stat_4d6_drop_lowest",
    "generate_stats",
    "outcome",
    "passive",
    "resolve_check",
    "roll_d20",
    "roll_d6",
    "roll_dice",
    "set_seed",
]
