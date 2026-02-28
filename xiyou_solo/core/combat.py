from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from xiyou_solo.core import rules


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ENEMY_PACKS_PATH = DATA_DIR / "enemy_packs.json"
ITEMS_PATH = DATA_DIR / "items.json"
SKILLS_PATH = DATA_DIR / "skills.json"


def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _default_enemy_packs() -> Dict[str, Any]:
    return {
        "bandits_1": {
            "name": "Bandit Ambush",
            "encounters": [
                {"enemies": [{"name": "Bandit Scout", "hp": 2, "ac": 12, "atk_dc": 12, "dmg": 1, "loot_gold": [3, 8]}]},
                {
                    "enemies": [
                        {"name": "Bandit Hound", "hp": 1, "ac": 11, "atk_dc": 11, "dmg": 1, "loot_gold": [1, 5]},
                        {"name": "Bandit Raider", "hp": 2, "ac": 12, "atk_dc": 12, "dmg": 1, "loot_gold": [2, 7]},
                    ]
                },
            ],
        }
    }


def _default_items() -> Dict[str, Any]:
    return {
        "dagger": {"id": "dagger", "type": "weapon", "roll_bonus": 1},
        "healing_herbs": {"id": "healing_herbs", "type": "consumable", "heal": 2},
        "buff_potion": {"id": "buff_potion", "type": "consumable", "roll_bonus": 2, "duration": 1},
        "incense_charm": {"id": "incense_charm", "type": "consumable", "roll_bonus": 1, "duration": 2},
        "smoke_bomb": {"id": "smoke_bomb", "type": "consumable", "effect": "flee_success"},
    }


def _default_skills() -> Dict[str, Any]:
    return {
        "class_skills": {
            "martial": ["power_strike"],
            "pilgrim_monk": ["steady_mind"],
            "talismanist": ["focus_charm"],
            "wanderer": ["quick_shot"],
        },
        "skills": {
            "power_strike": {"id": "power_strike", "attr": "body", "roll_bonus": 2, "extra_damage": 1, "cooldown": 2},
            "steady_mind": {"id": "steady_mind", "attr": "spirit", "roll_bonus": 2, "cooldown": 2},
            "focus_charm": {"id": "focus_charm", "attr": "wit", "roll_bonus": 2, "cooldown": 2},
            "quick_shot": {"id": "quick_shot", "attr": "luck", "roll_bonus": 1, "extra_damage": 1, "cooldown": 2},
        },
    }


def _enemy_packs() -> Dict[str, Any]:
    return _read_json(ENEMY_PACKS_PATH, _default_enemy_packs())


def _items() -> Dict[str, Any]:
    return _read_json(ITEMS_PATH, _default_items())


def _skills_data() -> Dict[str, Any]:
    return _read_json(SKILLS_PATH, _default_skills())


def get_attr_mod(state: Dict[str, Any], attr: str) -> int:
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    stats = player.get("stats", {}) if isinstance(player.get("stats"), dict) else {}
    try:
        stat = int(stats.get(attr, 10))
    except (TypeError, ValueError):
        stat = 10
    return rules.ability_mod(stat)


def is_combat_active(state: Dict[str, Any]) -> bool:
    cs = state.get("combat_state", {})
    return isinstance(cs, dict) and bool(cs.get("active", False))


def _alive_enemies(cs: Dict[str, Any]) -> List[Dict[str, Any]]:
    enemies = cs.get("enemies", [])
    if not isinstance(enemies, list):
        return []
    return [e for e in enemies if isinstance(e, dict) and int(e.get("hp", 0)) > 0]


def _build_encounter(pack_id: str, encounter: Dict[str, Any]) -> List[Dict[str, Any]]:
    enemies = encounter.get("enemies", []) if isinstance(encounter.get("enemies"), list) else []
    out: List[Dict[str, Any]] = []
    for idx, e in enumerate(enemies, start=1):
        if not isinstance(e, dict):
            continue
        out.append(
            {
                "id": f"{pack_id}_mob_{idx}",
                "name": str(e.get("name", f"Enemy {idx}")),
                "hp": max(1, int(e.get("hp", 1))),
                "ac": max(8, int(e.get("ac", 11))),
                "atk_dc": max(8, int(e.get("atk_dc", e.get("ac", 11)))),
                "dmg": max(1, int(e.get("dmg", 1))),
                "loot_gold": e.get("loot_gold", [1, 5]),
            }
        )
    if not out:
        out.append({"id": f"{pack_id}_mob_1", "name": "Enemy", "hp": 1, "ac": 11, "atk_dc": 11, "dmg": 1, "loot_gold": [1, 3]})
    return out


def start_combat(state: Dict[str, Any], enemy_pack_id: str) -> Dict[str, Any]:
    packs = _enemy_packs()
    pack = packs.get(enemy_pack_id, packs.get("bandits_1", {}))
    encounters = pack.get("encounters", []) if isinstance(pack.get("encounters"), list) else []
    if not encounters:
        encounters = _default_enemy_packs()["bandits_1"]["encounters"]
    encounters_total = max(1, min(3, len(encounters)))
    encounter_index = 1
    enemies = _build_encounter(str(enemy_pack_id), encounters[0] if encounters else {})
    max_round = max(2, min(4, int((encounters[0] if encounters else {}).get("max_round", rules.roll_dice(1, 3)[0] + 1))))

    state["combat_state"] = {
        "active": True,
        "enemy_pack_id": str(enemy_pack_id),
        "encounter_index": encounter_index,
        "encounters_total": encounters_total,
        "round": 1,
        "max_round": max_round,
        "enemies": enemies,
        "player_effects": [],
        "skill_cd": {},
        "loot_pending_gold": 0,
        "result": "",
        "log": [f"Combat started: {enemy_pack_id} ({encounter_index}/{encounters_total})."],
    }
    return state


def parse_combat_input(text: str) -> Dict[str, Any]:
    raw = (text or "").strip().lower()
    if raw in {"1", "attack"}:
        return {"type": "attack"}
    if raw.startswith("2") or raw.startswith("skill"):
        parts = raw.split(maxsplit=1)
        skill_id = parts[1].strip() if len(parts) > 1 else ""
        return {"type": "skill", "skill_id": skill_id}
    if raw.startswith("3") or raw.startswith("use "):
        parts = raw.split(maxsplit=1)
        item_id = parts[1].strip() if len(parts) > 1 else ""
        return {"type": "use_item", "item_id": item_id}
    if raw in {"4", "defend"}:
        return {"type": "defend"}
    if raw in {"5", "flee"}:
        return {"type": "flee"}
    return {"type": "attack"}


def _tick_effects(cs: Dict[str, Any]) -> None:
    effects = cs.get("player_effects", [])
    if not isinstance(effects, list):
        cs["player_effects"] = []
        return
    next_effects: List[Dict[str, Any]] = []
    for ef in effects:
        if not isinstance(ef, dict):
            continue
        turns = int(ef.get("turns", 0)) - 1
        if turns > 0:
            ef["turns"] = turns
            next_effects.append(ef)
    cs["player_effects"] = next_effects


def _active_roll_bonus(cs: Dict[str, Any]) -> int:
    total = 0
    for ef in cs.get("player_effects", []):
        if isinstance(ef, dict):
            total += int(ef.get("roll_bonus", 0))
    return total


def _weapon_bonus(state: Dict[str, Any]) -> int:
    items = _items()
    inv = state.get("player", {}).get("inventory", [])
    if not isinstance(inv, list):
        return 0
    for iid in inv:
        item = items.get(str(iid), {})
        if isinstance(item, dict) and item.get("type") == "weapon":
            return int(item.get("roll_bonus", 0))
    return 0


def _player_ref(state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(state.get("player"), dict):
        state["player"] = {}
    return state["player"]


def _enemy_attack(state: Dict[str, Any], cs: Dict[str, Any], mitigated: bool = False) -> int:
    alive = _alive_enemies(cs)
    if not alive:
        return 0
    dmg = sum(int(e.get("dmg", 1)) for e in alive[:2])
    if mitigated:
        dmg = max(0, dmg - 1)
    p = _player_ref(state)
    hp = int(p.get("hp", 12))
    p["hp"] = max(0, hp - dmg)
    return dmg


def _consume_item(inv: List[str], item_id: str) -> bool:
    if item_id in inv:
        inv.remove(item_id)
        return True
    return False


def apply_combat_action(state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    if not is_combat_active(state):
        return state
    cs = state.get("combat_state", {})
    if not isinstance(cs, dict):
        return state

    packs = _enemy_packs()
    items = _items()
    skills_data = _skills_data()
    class_skills = skills_data.get("class_skills", {}) if isinstance(skills_data.get("class_skills"), dict) else {}
    skills = skills_data.get("skills", {}) if isinstance(skills_data.get("skills"), dict) else {}

    player = _player_ref(state)
    inv = player.get("inventory", [])
    if not isinstance(inv, list):
        inv = []
        player["inventory"] = inv

    a_type = str(action.get("type", "attack"))
    round_no = int(cs.get("round", 1))
    max_round = int(cs.get("max_round", 4))
    cs.setdefault("log", [])

    if round_no > max_round:
        cs["active"] = False
        cs["result"] = "forced_end"

    if not bool(cs.get("active", False)):
        return state

    skill_bonus = 0
    skill_extra_damage = 0
    attr = "body"
    mitigated = False

    if a_type == "defend":
        cs.setdefault("player_effects", []).append({"type": "defend", "turns": 1})
        mitigated = True
        cs["log"].append("You defend this round.")
    elif a_type == "flee":
        roll = rules.roll_d20("normal")
        total = int(roll["d20"]) + get_attr_mod(state, "luck")
        if total >= 12:
            cs["active"] = False
            cs["result"] = "flee"
            cs["log"].append("You escaped from combat.")
            return state
        cs["log"].append(f"Flee failed ({total} vs 12).")
    elif a_type == "use_item":
        item_id = str(action.get("item_id", "")).strip()
        if not item_id and inv:
            item_id = str(inv[0])
        item = items.get(item_id, {}) if isinstance(items.get(item_id), dict) else {}
        if not item or not _consume_item(inv, item_id):
            cs["log"].append(f"Item use failed: {item_id or 'none'}.")
        else:
            heal = int(item.get("heal", 0))
            if heal > 0:
                hp = int(player.get("hp", 12))
                max_hp = int(player.get("max_hp", 12))
                player["hp"] = min(max_hp, hp + heal)
            roll_bonus = int(item.get("roll_bonus", 0))
            duration = max(1, int(item.get("duration", 1)))
            if roll_bonus:
                cs.setdefault("player_effects", []).append({"type": "buff", "turns": duration, "roll_bonus": roll_bonus})
            effect = str(item.get("effect", ""))
            if effect == "flee_success":
                cs.setdefault("player_effects", []).append({"type": "flee_success", "turns": 1})
            if effect == "enemy_roll_penalty":
                cs.setdefault("player_effects", []).append({"type": "enemy_penalty", "turns": 1})
            cs["log"].append(f"Used item: {item_id}.")
    elif a_type == "skill":
        class_id = str(player.get("class_id", "martial"))
        allow = class_skills.get(class_id, [])
        if not isinstance(allow, list):
            allow = []
        skill_id = str(action.get("skill_id", "")).strip() or (str(allow[0]) if allow else "")
        cd = cs.setdefault("skill_cd", {})
        cooldown_left = int(cd.get(skill_id, 0)) if isinstance(cd, dict) else 0
        if skill_id and skill_id in allow and cooldown_left <= 0:
            sk = skills.get(skill_id, {}) if isinstance(skills.get(skill_id), dict) else {}
            skill_bonus = int(sk.get("roll_bonus", 0))
            skill_extra_damage = int(sk.get("extra_damage", 0))
            attr = str(sk.get("attr", "body"))
            cd[skill_id] = int(sk.get("cooldown", 2))
            cs["log"].append(f"Skill used: {skill_id}.")
        else:
            cs["log"].append(f"Skill unavailable: {skill_id or 'none'}.")
            a_type = "attack"

    hit = False
    nat = None
    if a_type in {"attack", "skill"}:
        enemy = _alive_enemies(cs)[0] if _alive_enemies(cs) else None
        if enemy:
            roll = rules.roll_d20("normal")
            nat = int(roll["d20"])
            total = nat + get_attr_mod(state, attr) + _weapon_bonus(state) + _active_roll_bonus(cs) + skill_bonus
            ac = int(enemy.get("ac", 11))
            hit = total >= ac
            if nat == 1:
                player["hp"] = max(0, int(player.get("hp", 12)) - 1)
                cs["log"].append("Critical miss: you hurt yourself for 1 HP.")
            if hit:
                dmg = 1 + skill_extra_damage
                if nat == 20 or total >= ac + 5:
                    dmg += 1
                enemy["hp"] = max(0, int(enemy.get("hp", 1)) - dmg)
                cs["log"].append(f"Hit {enemy.get('name','enemy')} for {dmg} (roll {total} vs AC {ac}).")
                if enemy["hp"] <= 0:
                    lg = enemy.get("loot_gold", [1, 3])
                    if isinstance(lg, list) and len(lg) >= 2:
                        lo = int(lg[0])
                        hi = int(lg[1])
                    else:
                        lo, hi = 1, 3
                    lo, hi = (lo, hi) if lo <= hi else (hi, lo)
                    cs["loot_pending_gold"] = int(cs.get("loot_pending_gold", 0)) + rules.roll_dice(1, hi - lo + 1)[0] + lo - 1
            else:
                cs["log"].append(f"Missed (roll {total} vs AC {ac}).")

    if _alive_enemies(cs):
        if (a_type in {"attack", "skill"} and not hit) or a_type in {"defend", "flee", "use_item"}:
            dmg = _enemy_attack(state, cs, mitigated=mitigated)
            if dmg > 0:
                cs["log"].append(f"Enemies retaliate for {dmg} damage.")

    if int(_player_ref(state).get("hp", 0)) <= 0:
        cs["active"] = False
        cs["result"] = "defeat"
        cs["log"].append("You are down.")
        return state

    if not _alive_enemies(cs):
        idx = int(cs.get("encounter_index", 1))
        total = int(cs.get("encounters_total", 1))
        if idx < total:
            pack = packs.get(str(cs.get("enemy_pack_id", "bandits_1")), _default_enemy_packs()["bandits_1"])
            encounters = pack.get("encounters", []) if isinstance(pack.get("encounters"), list) else []
            next_encounter = encounters[idx] if idx < len(encounters) else {"enemies": [{"name": "Enemy", "hp": 1, "ac": 11, "dmg": 1}]}
            cs["encounter_index"] = idx + 1
            cs["round"] = 1
            cs["max_round"] = max(2, min(4, int(next_encounter.get("max_round", rules.roll_dice(1, 3)[0] + 1))))
            cs["enemies"] = _build_encounter(str(cs.get("enemy_pack_id", "bandits_1")), next_encounter)
            cs["log"].append(f"Encounter {idx} cleared. Next encounter begins.")
            _tick_effects(cs)
            return state
        cs["active"] = False
        cs["result"] = "victory"
        cs["log"].append("All encounters cleared.")
        return state

    cs["round"] = int(cs.get("round", 1)) + 1
    if int(cs.get("round", 1)) > int(cs.get("max_round", 4)) and _alive_enemies(cs):
        # forced ending to keep fast15 pacing
        p = _player_ref(state)
        hp = int(p.get("hp", 12))
        gold = int(p.get("gold", 0))
        if hp > 1:
            p["hp"] = hp - 1
            cs["log"].append("Forced ending: you retreat with 1 HP loss.")
        elif gold >= 5:
            p["gold"] = gold - 5
            cs["log"].append("Forced ending: you lose 5 gold while retreating.")
        else:
            state["threat"] = max(0, int(state.get("threat", 0)) + 1)
            cs["log"].append("Forced ending: pressure increases (threat +1).")
        cs["active"] = False
        cs["result"] = "forced_end"
        return state

    _tick_effects(cs)
    cd = cs.get("skill_cd", {})
    if isinstance(cd, dict):
        for k in list(cd.keys()):
            left = int(cd.get(k, 0)) - 1
            cd[k] = max(0, left)

    return state


def finalize_combat(state: Dict[str, Any]) -> Dict[str, Any]:
    cs = state.get("combat_state", {})
    if not isinstance(cs, dict):
        return state
    player = _player_ref(state)
    result = str(cs.get("result", ""))
    if result == "victory":
        reward = int(cs.get("loot_pending_gold", 0))
        player["gold"] = int(player.get("gold", 0)) + reward
        # basic drop
        if rules.roll_dice(1, 100)[0] <= 30:
            inv = player.get("inventory", [])
            if isinstance(inv, list):
                inv.append("healing_herbs")
        cs.setdefault("log", []).append(f"Victory reward: +{reward} gold.")
    elif result == "defeat":
        cs.setdefault("log", []).append("Defeat: no loot.")
    elif result == "flee":
        cs.setdefault("log", []).append("You fled. No loot gained.")
    elif result == "forced_end":
        cs.setdefault("log", []).append("Combat ended by time pressure.")

    state["combat_state"] = {
        "active": False,
        "result": result,
        "log": cs.get("log", []),
    }
    return state


def get_combat_prompt(state: Dict[str, Any]) -> str:
    cs = state.get("combat_state", {})
    if not isinstance(cs, dict):
        return "No combat."
    if not bool(cs.get("active", False)):
        log = cs.get("log", [])
        tail = log[-3:] if isinstance(log, list) else []
        suffix = "\n".join([str(x) for x in tail]) if tail else "Combat ended."
        return f"[combat] ended ({cs.get('result', 'unknown')}).\n{suffix}"

    player = _player_ref(state)
    hp = int(player.get("hp", 12))
    max_hp = int(player.get("max_hp", 12))
    round_no = int(cs.get("round", 1))
    max_round = int(cs.get("max_round", 4))
    enemies = _alive_enemies(cs)
    enemy_lines = ", ".join([f"{e.get('name','enemy')} HP:{int(e.get('hp',0))}" for e in enemies]) or "none"
    class_id = str(player.get("class_id", "martial"))
    skills_data = _skills_data()
    class_skills = skills_data.get("class_skills", {}) if isinstance(skills_data.get("class_skills"), dict) else {}
    skills = class_skills.get(class_id, []) if isinstance(class_skills.get(class_id), list) else []
    skill_hint = ",".join([str(s) for s in skills]) if skills else "none"

    return (
        f"[combat] {cs.get('enemy_pack_id','pack')} encounter {cs.get('encounter_index',1)}/{cs.get('encounters_total',1)}\n"
        f"Round {round_no}/{max_round}  HP {hp}/{max_hp}\n"
        f"Enemies: {enemy_lines}\n"
        f"Skills: {skill_hint}\n"
        "Actions:\n"
        "1) attack\n"
        "2) skill <skill_id>\n"
        "3) use <item_id>\n"
        "4) defend\n"
        "5) flee"
    )
