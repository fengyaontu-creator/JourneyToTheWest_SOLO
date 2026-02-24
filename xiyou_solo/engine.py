from __future__ import annotations

import random
from typing import Any, Dict, List, Literal, Tuple


_rng = random.Random()


def set_seed(seed: int | None) -> None:
    if seed is None:
        _rng.seed()
        return
    _rng.seed(int(seed))


def roll_dice(n: int, sides: int) -> List[int]:
    return [_rng.randint(1, sides) for _ in range(n)]


def roll_d6(n: int = 1) -> int:
    return sum(roll_dice(n, 6))


def roll_d20(mode: Literal["normal", "adv", "dis"] = "normal") -> Dict[str, Any]:
    a = _rng.randint(1, 20)
    if mode == "normal":
        return {"mode": "normal", "d20": a, "rolls": [a]}
    b = _rng.randint(1, 20)
    if mode == "adv":
        return {"mode": "adv", "d20": max(a, b), "rolls": [a, b]}
    return {"mode": "dis", "d20": min(a, b), "rolls": [a, b]}


def ability_mod(stat: int) -> int:
    return (int(stat) - 10) // 2


def passive(stat: int) -> int:
    return 10 + ability_mod(stat)


def gen_stat_3d6() -> Tuple[int, List[int]]:
    rolls = roll_dice(3, 6)
    return sum(rolls), rolls


def gen_stat_4d6_drop_lowest() -> Tuple[int, List[int]]:
    rolls = roll_dice(4, 6)
    s = sorted(rolls)
    return sum(s[1:]), rolls


def generate_stats(method: Literal["3d6", "4d6dl"] = "3d6") -> Dict[str, Any]:
    stats: Dict[str, int] = {}
    details: Dict[str, List[int]] = {}
    for attr in ("body", "wit", "spirit", "luck"):
        if method == "4d6dl":
            val, rolls = gen_stat_4d6_drop_lowest()
        else:
            val, rolls = gen_stat_3d6()
        stats[attr] = max(3, min(18, int(val)))
        details[attr] = rolls
    return {"stats": stats, "details": details, "method": method}


def resolve_check(
    stat: int,
    dc: int,
    bonus: int = 0,
    mode: Literal["normal", "adv", "dis"] = "normal",
    use_passive: bool = False,
) -> Dict[str, Any]:
    mod = ability_mod(stat)
    if use_passive:
        total = passive(stat) + int(bonus)
        return {
            "passive": True,
            "mode": "passive",
            "d20": None,
            "rolls": [],
            "mod": mod,
            "bonus": int(bonus),
            "total": total,
            "dc": int(dc),
            "success": total >= int(dc),
        }

    d = roll_d20(mode)
    total = int(d["d20"]) + mod + int(bonus)
    return {
        "passive": False,
        "mode": d["mode"],
        "d20": int(d["d20"]),
        "rolls": list(d["rolls"]),
        "mod": mod,
        "bonus": int(bonus),
        "total": total,
        "dc": int(dc),
        "success": total >= int(dc),
    }


def outcome(total: int, dc: int) -> str:
    if total >= dc + 5:
        return "outcome_critical"
    if total >= dc:
        return "outcome_success"
    if total >= dc - 3:
        return "outcome_partial"
    if total >= dc - 8:
        return "outcome_fail"
    return "outcome_fumble"

