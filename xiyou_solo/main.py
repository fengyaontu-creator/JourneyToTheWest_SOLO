from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import engine
from game_data import ATTR_LABEL, ATTRS, CLASSES, EVENT_POOL, ITEMS, QUESTS, RACES
from i18n import t
from llm_client import generate_dm_reply, is_online_available
from io_cli import loc, parse_command, print_choices, print_hud, print_inventory, print_shop
from parser import parse_dm_output
from storage import (
    append_event,
    clear_current_session_id,
    delete_session,
    ensure_dirs,
    get_current_session_id,
    list_sessions,
    load_session,
    make_session_id,
    save_session,
    set_current_session_id,
)


QUIT_WORDS = {"quit", "exit", "q"}
BASE_DIR = Path(__file__).resolve().parent
DM_SYSTEM_PATH = BASE_DIR / "prompts" / "dm_system.txt"
ATTITUDE_STEPS = ("hostile", "unfriendly", "neutral", "friendly", "allied")


def _read_dm_system() -> str:
    if DM_SYSTEM_PATH.exists():
        return DM_SYSTEM_PATH.read_text(encoding="utf-8")
    return (
        "You are a light myth DM in post-pilgrimage Journey world. "
        "Output Narrative plus Directive JSON."
    )


def _calc_derived(player: Dict[str, Any]) -> None:
    stats = player["stats"]
    mods = {k: engine.ability_mod(v) for k, v in stats.items()}
    passives = {k: 10 + mods[k] for k in stats}
    player["mods"] = mods
    player["passives"] = passives


def _ensure_runtime_fields(state: Dict[str, Any]) -> None:
    state.setdefault("language", "zh")
    state.setdefault("seed", None)
    state.setdefault("combat", None)
    story = state.setdefault("story", {})
    story.setdefault("flags", [])
    story.setdefault("quest_id", "")
    story.setdefault("quest_title", {"zh": "", "en": ""})
    story.setdefault("current_goal", {"zh": "", "en": ""})
    story.setdefault("reward_gold_range", [40, 80])
    story.setdefault("tags", [])
    story.setdefault("location", {"zh": "路边茶棚", "en": "Roadside Tea Stall"})
    story.setdefault("turn", 0)
    story.setdefault("progress", 0)
    story.setdefault("required_progress", 4)
    story.setdefault("threat_level", 1)
    story.setdefault("completed", False)
    story.setdefault("world_tick", 0)
    story.setdefault("day", 1)
    story.setdefault("clock", 8)

    player = state.setdefault("player", {})
    player.setdefault("stats", {"body": 10, "wit": 10, "spirit": 10, "luck": 10})
    player.setdefault("temp_effects", {"next_bonus": {}, "next_adv_tags": []})
    player.setdefault("once_flags", {"simple_armor_applied": False})
    if "mods" not in player or "passives" not in player:
        _calc_derived(player)

    npcs = state.setdefault("npcs", [])
    if not isinstance(npcs, list):
        state["npcs"] = []
        npcs = state["npcs"]
    for npc in npcs:
        if not isinstance(npc, dict):
            continue
        npc.setdefault("id", "")
        npc.setdefault("name", {"zh": "", "en": ""})
        if "attitude_score" not in npc:
            raw = str(npc.get("attitude", "neutral")).strip().lower()
            npc["attitude_score"] = max(-2, min(2, ATTITUDE_STEPS.index(raw) - 2 if raw in ATTITUDE_STEPS else 0))
        npc["attitude"] = ATTITUDE_STEPS[max(0, min(4, int(npc["attitude_score"]) + 2))]


def _default_state(session_id: str) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "language": "zh",
        "seed": None,
        "player": {
            "name": "",
            "race_id": "",
            "class_id": "",
            "stats": {"body": 10, "wit": 10, "spirit": 10, "luck": 10},
            "mods": {},
            "passives": {},
            "max_hp": 12,
            "hp": 12,
            "gold": 50,
            "inventory": [],
            "resources": {},
            "temp_effects": {"next_bonus": {}, "next_adv_tags": []},
            "once_flags": {"simple_armor_applied": False},
        },
        "story": {
            "quest_id": "",
            "quest_title": {"zh": "", "en": ""},
            "current_goal": {"zh": "", "en": ""},
            "reward_gold_range": [40, 80],
            "tags": [],
            "location": {"zh": "路边茶棚", "en": "Roadside Tea Stall"},
            "turn": 0,
            "progress": 0,
            "required_progress": 4,
            "threat_level": 1,
            "completed": False,
            "flags": [],
            "world_tick": 0,
            "day": 1,
            "clock": 8,
        },
        "npcs": [],
        "combat": None,
    }


def _default_log(session_id: str) -> Dict[str, Any]:
    return {"session_id": session_id, "events": []}


def _ask(text: str) -> str:
    return input(text).strip()


def _pick_language_from_cmd(state: Dict[str, Any], log_data: Dict[str, Any], cmd: str) -> bool:
    parts = parse_command(cmd.lower())
    if not parts:
        return False
    if parts[0] in {"zh", "en"}:
        state["language"] = parts[0]
    elif parts[0] == "lang" and len(parts) == 2 and parts[1] in {"zh", "en"}:
        state["language"] = parts[1]
    else:
        return False
    lang = state["language"]
    append_event(log_data, "update", "language_changed", {"language": lang})
    print(t("lang_switched", lang))
    save_session(state, log_data)
    return True


def _pick_seed(state: Dict[str, Any], log_data: Dict[str, Any], cmd: str) -> bool:
    parts = parse_command(cmd)
    if len(parts) != 2 or parts[0].lower() != "seed":
        return False
    try:
        seed = int(parts[1])
    except ValueError:
        return True
    state["seed"] = seed
    engine.set_seed(seed)
    append_event(log_data, "update", "seed_set", {"seed": seed})
    print(t("seed_set", state["language"], seed=seed))
    save_session(state, log_data)
    return True


def _apply_race_creation_bonus(state: Dict[str, Any], race_id: str) -> None:
    race = RACES[race_id]
    if race_id != "human":
        return
    # Human can pick any two attributes +1 at creation.
    chosen: List[str] = []
    lang = state["language"]
    while len(chosen) < 2:
        opts = [f"{i+1}) {ATTR_LABEL[a][lang]}" for i, a in enumerate(ATTRS)]
        print_choices("Pick two bonus attributes / 选择两项加值：", opts)
        raw = _ask("> ")
        if not raw.isdigit():
            continue
        idx = int(raw) - 1
        if 0 <= idx < len(ATTRS):
            attr = ATTRS[idx]
            if attr not in chosen:
                chosen.append(attr)
    for attr in chosen:
        state["player"]["stats"][attr] = min(18, int(state["player"]["stats"][attr]) + 1)


def _create_character(state: Dict[str, Any], log_data: Dict[str, Any]) -> None:
    lang = state["language"]
    name = _ask(t("input_name", lang))
    while not name:
        name = _ask(t("input_name", lang))
    state["player"]["name"] = name

    race_rows = [f"{i+1}) {loc(v['name'], lang)} - {loc(v['desc'], lang)} ({rid})" for i, (rid, v) in enumerate(RACES.items())]
    print_choices("Races / 种族", race_rows)
    race_ids = list(RACES.keys())
    race_pick = _ask(t("pick_race", lang))
    race_idx = int(race_pick) - 1 if race_pick.isdigit() else 0
    race_idx = max(0, min(race_idx, len(race_ids) - 1))
    race_id = race_ids[race_idx]
    state["player"]["race_id"] = race_id

    class_rows = [f"{i+1}) {loc(v['name'], lang)} - {loc(v['desc'], lang)} ({cid})" for i, (cid, v) in enumerate(CLASSES.items())]
    print_choices("Classes / 职业", class_rows)
    class_ids = list(CLASSES.keys())
    class_pick = _ask(t("pick_class", lang))
    class_idx = int(class_pick) - 1 if class_pick.isdigit() else 0
    class_idx = max(0, min(class_idx, len(class_ids) - 1))
    class_id = class_ids[class_idx]
    state["player"]["class_id"] = class_id

    method = "4d6dl" if _ask(t("pick_roll_method", lang)).strip() == "2" else "3d6"
    gen = engine.generate_stats(method)
    state["player"]["stats"] = dict(gen["stats"])

    race_bonus = RACES[race_id].get("stat_bonus", {})
    for attr in ATTRS:
        state["player"]["stats"][attr] = min(18, max(3, int(state["player"]["stats"][attr]) + int(race_bonus.get(attr, 0))))
    _apply_race_creation_bonus(state, race_id)

    _calc_derived(state["player"])
    state["player"]["max_hp"] = 12 + state["player"]["mods"]["body"]
    state["player"]["hp"] = state["player"]["max_hp"]
    state["player"]["gold"] = 50 + int(RACES[race_id].get("starting_gold_bonus", 0))
    state["player"]["inventory"] = list(CLASSES[class_id].get("starter_items", []))
    state["player"]["resources"] = dict(CLASSES[class_id].get("resources", {}))

    append_event(
        log_data,
        "update",
        "character_created",
        {
            "name": name,
            "race_id": race_id,
            "class_id": class_id,
            "stats": state["player"]["stats"],
            "roll_method": method,
            "roll_details": gen["details"],
        },
    )


def _choose_quest(state: Dict[str, Any], log_data: Dict[str, Any]) -> None:
    lang = state["language"]
    quest_ids = list(QUESTS.keys())
    rows = [f"{i+1}) {loc(q['title'], lang)} - {loc(q['hook'], lang)}" for i, q in enumerate(QUESTS.values())]
    print_choices("Quest Hooks / 任务钩子", rows)
    pick = _ask(t("pick_quest", lang)).lower()
    if pick == "random":
        quest_id = random.choice(quest_ids)
    elif pick.isdigit() and 1 <= int(pick) <= len(quest_ids):
        quest_id = quest_ids[int(pick) - 1]
    else:
        quest_id = quest_ids[0]

    q = QUESTS[quest_id]
    story = state["story"]
    story["quest_id"] = quest_id
    story["quest_title"] = dict(q["title"])
    story["current_goal"] = dict(q["goal"])
    story["reward_gold_range"] = list(q["reward_gold_range"])
    story["tags"] = list(q["tags"])
    story["location"] = dict(q["start_location"])
    story["turn"] = 0
    story["progress"] = 0
    story["required_progress"] = 4
    story["threat_level"] = 1
    story["completed"] = False
    append_event(
        log_data,
        "scene",
        "quest_selected",
        {"quest_id": quest_id, "quest_title": q["title"], "goal": q["goal"], "reward_gold_range": q["reward_gold_range"]},
    )
    print(f"{loc(q['title'], lang)}")
    print(f"- {loc(q['hook'], lang)}")
    print(f"- {loc(q['goal'], lang)}")


def _new_game_flow() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    sid = make_session_id()
    state = _default_state(sid)
    log_data = _default_log(sid)
    _ensure_runtime_fields(state)
    lang = state["language"]
    print(t("new_start", lang))
    _choose_quest(state, log_data)
    _create_character(state, log_data)
    append_event(log_data, "scene", "chapter_1_start", {"location": state["story"]["location"], "quest_id": state["story"]["quest_id"]})
    save_session(state, log_data)
    return state, log_data


def _list_sessions(lang: str) -> None:
    ids = list_sessions()
    if not ids:
        print(t("list_none", lang))
        return
    print(t("list_title", lang))
    for sid in ids:
        print(f"- {sid}")


def _load_session_cmd(sid: str, lang: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    pair = load_session(sid)
    if not pair:
        print(t("invalid_cmd", lang))
        return None
    state, log_data = pair
    set_current_session_id(sid)
    if state.get("seed") is not None:
        engine.set_seed(int(state["seed"]))
    print(t("loaded", state.get("language", "zh"), sid=sid))
    return state, log_data


def _boot_menu() -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    lang = "zh"
    print(t("title", lang))
    print(t("boot_hint", lang))
    while True:
        cmd = _ask("> ")
        parts = parse_command(cmd)
        if not parts:
            continue
        head = parts[0].lower()
        if head in QUIT_WORDS:
            print(t("exit", lang))
            return None
        if head == "new":
            state, log_data = _new_game_flow()
            set_current_session_id(state["session_id"])
            return state, log_data
        if head == "list":
            _list_sessions(lang)
            continue
        if head == "load" and len(parts) == 2:
            pair = _load_session_cmd(parts[1], lang)
            if pair:
                return pair
            continue
        if head == "delete" and len(parts) == 2:
            ok = delete_session(parts[1])
            if ok:
                print(t("deleted", lang, sid=parts[1]))
            else:
                print(t("invalid_cmd", lang))
            continue
        print(t("invalid_cmd", lang))


def _pick_event(state: Dict[str, Any], action_text: str) -> Dict[str, Any]:
    tags = list(state["story"]["tags"]) or ["social"]
    if any(k in action_text.lower() for k in ("look", "查", "观察", "inspect")):
        preferred = "mist" if "mist" in tags else tags[0]
    elif any(k in action_text.lower() for k in ("talk", "劝", "说服", "聊")):
        preferred = "social" if "social" in tags else tags[0]
    else:
        preferred = random.choice(tags)

    pool = EVENT_POOL.get(preferred) or EVENT_POOL.get(tags[0]) or EVENT_POOL["social"]
    event = random.choice(pool)
    return dict(event)


def _build_dm_context(state: Dict[str, Any], log_data: Dict[str, Any], recent_n: int = 12) -> str:
    lang = state.get("language", "zh")
    story = state["story"]
    player = state["player"]
    npcs = state.get("npcs", [])
    npc_brief = [f"{n.get('id', '')}:{n.get('attitude', 'neutral')}" for n in npcs[:8] if isinstance(n, dict)]
    flags = list(story.get("flags", []))
    recent = log_data.get("events", [])[-recent_n:]
    lines = [
        f"language: {lang}",
        f"session_id: {state.get('session_id', '')}",
        f"quest_id: {story.get('quest_id', '')}",
        f"quest_title: {loc(story.get('quest_title', {}), lang)}",
        f"goal: {loc(story.get('current_goal', {}), lang)}",
        f"location: {loc(story.get('location', {}), lang)}",
        f"turn: {story.get('turn', 0)}",
        f"world_tick: {story.get('world_tick', 0)}",
        f"day: {story.get('day', 1)}",
        f"clock: {story.get('clock', 8)}",
        f"progress: {story.get('progress', 0)}/{story.get('required_progress', 4)}",
        f"threat_level: {story.get('threat_level', 1)}",
        f"flags: {flags[-10:]}",
        f"npcs: {npc_brief}",
        f"player_name: {player.get('name', '')}",
        f"hp: {player.get('hp', 0)}/{player.get('max_hp', 0)}",
        f"gold: {player.get('gold', 0)}",
        f"inventory: {player.get('inventory', [])}",
        "recent_events:",
    ]
    for ev in recent:
        lines.append(f"- [{ev.get('type', 'unknown')}] {ev.get('content', '')}")
    return "\n".join(lines)


def _directive_attr_to_internal(attr: str) -> str:
    table = {"Body": "body", "Mind": "wit", "Spirit": "spirit", "Luck": "luck"}
    return table.get(attr, "wit")


def _start_combat_from_directive(state: Dict[str, Any], pack_id: str) -> None:
    base_hp = {
        "imp_pair": 8,
        "sand_raider": 10,
        "bone_scout": 9,
        "fan_guard": 11,
        "court_mischief": 7,
    }.get(pack_id, 8)
    state["combat"] = {"enemy_pack_id": pack_id or "imp_pair", "enemy_hp": base_hp, "round": 1}


def _consume_temp_effects(player: Dict[str, Any], attr: str, event_tags: List[str]) -> Tuple[int, str]:
    bonus = 0
    mode = "normal"
    temp = player.setdefault("temp_effects", {"next_bonus": {}, "next_adv_tags": []})
    next_bonus: Dict[str, int] = temp.get("next_bonus", {})
    if attr in next_bonus:
        bonus += int(next_bonus.pop(attr))
    adv_tags: List[str] = temp.get("next_adv_tags", [])
    if any(tag in adv_tags for tag in event_tags):
        mode = "adv"
        temp["next_adv_tags"] = []
    return bonus, mode


def _append_story_flag(story: Dict[str, Any], flag: str) -> bool:
    text = str(flag).strip()
    if not text:
        return False
    flags = story.setdefault("flags", [])
    if text in flags:
        return False
    flags.append(text)
    return True


def _attitude_from_score(score: int) -> str:
    return ATTITUDE_STEPS[max(0, min(4, int(score) + 2))]


def _find_or_create_npc(state: Dict[str, Any], npc_id: str, name: str = "") -> Dict[str, Any]:
    npcs = state.setdefault("npcs", [])
    for npc in npcs:
        if str(npc.get("id", "")) == npc_id:
            return npc
    label = name.strip() or npc_id
    npc = {"id": npc_id, "name": {"zh": label, "en": label}, "attitude_score": 0, "attitude": "neutral"}
    npcs.append(npc)
    return npc


def _apply_npc_attitude_changes(state: Dict[str, Any], log_data: Dict[str, Any], changes: List[Dict[str, Any]]) -> None:
    for row in changes:
        npc_id = str(row.get("npc_id", "")).strip()
        if not npc_id:
            continue
        npc = _find_or_create_npc(state, npc_id, str(row.get("name", "")))
        old_score = int(npc.get("attitude_score", 0))
        set_to = str(row.get("set_to", "")).strip().lower()
        if set_to in ATTITUDE_STEPS:
            new_score = ATTITUDE_STEPS.index(set_to) - 2
        else:
            delta = int(row.get("delta", 0))
            new_score = old_score + delta
        new_score = max(-2, min(2, new_score))
        if new_score == old_score:
            continue
        npc["attitude_score"] = new_score
        npc["attitude"] = _attitude_from_score(new_score)
        append_event(
            log_data,
            "update",
            "npc_attitude_changed",
            {
                "npc_id": npc_id,
                "before": _attitude_from_score(old_score),
                "after": npc["attitude"],
                "delta": new_score - old_score,
                "reason": str(row.get("reason", "")),
            },
        )


def _run_world_tick(state: Dict[str, Any], log_data: Dict[str, Any], directive: Dict[str, Any], turn_outcome: str) -> None:
    story = state["story"]
    wt = directive.get("world_tick", {}) if isinstance(directive.get("world_tick", {}), dict) else {}
    tick = int(story.get("world_tick", 0)) + 1
    story["world_tick"] = tick

    clock_delta = int(wt.get("clock_delta", 1))
    clock_delta = max(1, min(6, clock_delta))
    clock = int(story.get("clock", 8)) + clock_delta
    day = int(story.get("day", 1))
    while clock >= 24:
        clock -= 24
        day += 1
    story["clock"] = clock
    story["day"] = day

    threat_delta = int(wt.get("threat_delta", 0))
    if turn_outcome in {"outcome_fail", "outcome_fumble", "passive_fail"}:
        threat_delta += 1
    elif turn_outcome in {"outcome_critical", "outcome_success", "passive_success"}:
        threat_delta -= 1
    story["threat_level"] = max(0, min(9, int(story.get("threat_level", 1)) + threat_delta))

    if int(story["threat_level"]) >= 4:
        _append_story_flag(story, "high_threat")

    append_event(
        log_data,
        "world_tick",
        "world_tick",
        {
            "tick": tick,
            "day": day,
            "clock": clock,
            "clock_delta": clock_delta,
            "threat_delta": threat_delta,
            "threat_level": story["threat_level"],
            "notes": str(wt.get("notes", "")),
        },
    )


def _apply_outcome(state: Dict[str, Any], log_data: Dict[str, Any], event: Dict[str, Any], check: Dict[str, Any], outcome_key: str) -> str:
    story = state["story"]
    player = state["player"]
    etype = event["type"]
    if check["passive"]:
        if check["success"]:
            story["progress"] += 1 if etype == "clue" else 0
            return "passive_success"
        story["threat_level"] += 1
        return "passive_fail"

    if etype == "clue":
        if outcome_key == "outcome_critical":
            story["progress"] += 2
        elif outcome_key == "outcome_success":
            story["progress"] += 1
        elif outcome_key == "outcome_partial":
            story["progress"] += 1
            story["threat_level"] += 1
            player["hp"] = max(1, int(player["hp"]) - 1)
        elif outcome_key == "outcome_fail":
            story["threat_level"] += 1
        else:
            story["threat_level"] += 2
            player["hp"] = max(1, int(player["hp"]) - 2)
    elif etype == "hazard":
        if outcome_key in {"outcome_fail", "outcome_fumble"}:
            dmg = 2 if outcome_key == "outcome_fail" else 4
            player["hp"] = max(1, int(player["hp"]) - dmg)
            story["threat_level"] += 1 if outcome_key == "outcome_fail" else 2
        elif outcome_key == "outcome_partial":
            player["hp"] = max(1, int(player["hp"]) - 1)
            story["threat_level"] += 1
    elif etype == "reward":
        gain = random.randint(5, 20)
        player["gold"] += gain
        append_event(log_data, "gold_change", "event_reward", {"delta": gain, "gold": player["gold"]})
    elif etype == "mislead":
        if outcome_key in {"outcome_fail", "outcome_fumble"}:
            story["threat_level"] += 1
        else:
            story["progress"] += 1
    return outcome_key


def _check_quest_completion(state: Dict[str, Any], log_data: Dict[str, Any]) -> Optional[int]:
    story = state["story"]
    if story["completed"]:
        return None
    if int(story["progress"]) < int(story["required_progress"]):
        return None
    low, high = story["reward_gold_range"]
    reward = random.randint(int(low), int(high))
    state["player"]["gold"] += reward
    story["completed"] = True
    story["current_goal"] = {
        "zh": "任务已完成，准备返程或开启新任务。",
        "en": "Quest complete. Return or start a new one.",
    }
    append_event(log_data, "gold_change", "quest_reward", {"delta": reward, "gold": state["player"]["gold"]})
    append_event(log_data, "update", "quest_completed", {"quest_id": story["quest_id"], "reward": reward})
    return reward


def _use_item(state: Dict[str, Any], log_data: Dict[str, Any], item_id: str) -> None:
    lang = state["language"]
    inv = state["player"]["inventory"]
    if item_id not in inv:
        print(t("use_missing", lang, item_id=item_id))
        return
    item = ITEMS.get(item_id)
    if not item:
        print(t("use_missing", lang, item_id=item_id))
        return
    effect = item.get("effect", {})
    etype = effect.get("type")
    if etype == "heal":
        n, sides = effect.get("dice", [1, 6])
        heal = sum(engine.roll_dice(int(n), int(sides))) + int(effect.get("bonus", 0))
        state["player"]["hp"] = min(int(state["player"]["max_hp"]), int(state["player"]["hp"]) + heal)
        append_event(log_data, "item_use", "heal", {"item_id": item_id, "heal": heal, "hp": state["player"]["hp"]})
    elif etype == "next_bonus":
        attr = str(effect.get("attr", "body"))
        bonus = int(effect.get("bonus", 0))
        next_bonus = state["player"]["temp_effects"].setdefault("next_bonus", {})
        next_bonus[attr] = int(next_bonus.get(attr, 0)) + bonus
        append_event(log_data, "item_use", "next_bonus", {"item_id": item_id, "attr": attr, "bonus": bonus})
    elif etype == "next_advantage":
        tags = list(effect.get("tags", []))
        state["player"]["temp_effects"]["next_adv_tags"] = tags
        append_event(log_data, "item_use", "next_advantage", {"item_id": item_id, "tags": tags})
    elif etype == "max_hp_once":
        if not state["player"]["once_flags"].get("simple_armor_applied", False):
            bonus = int(effect.get("bonus", 2))
            state["player"]["max_hp"] += bonus
            state["player"]["hp"] += bonus
            state["player"]["once_flags"]["simple_armor_applied"] = True
            append_event(log_data, "item_use", "max_hp_once", {"item_id": item_id, "bonus": bonus})
    inv.remove(item_id)
    print(t("use_ok", lang, item=loc(item["name"], lang)))
    save_session(state, log_data)


def _buy_item(state: Dict[str, Any], log_data: Dict[str, Any], item_id: str, qty: int) -> None:
    lang = state["language"]
    item = ITEMS.get(item_id)
    if not item:
        print(t("invalid_cmd", lang))
        return
    qty = max(1, qty)
    total_cost = int(item["price"]) * qty
    if int(state["player"]["gold"]) < total_cost:
        print(t("buy_no_money", lang))
        return
    state["player"]["gold"] -= total_cost
    for _ in range(qty):
        state["player"]["inventory"].append(item_id)
    append_event(log_data, "gold_change", "buy_item", {"delta": -total_cost, "gold": state["player"]["gold"]})
    append_event(log_data, "item_use", "buy", {"item_id": item_id, "qty": qty})
    print(t("buy_ok", lang, item=loc(item["name"], lang), qty=qty, cost=total_cost))
    save_session(state, log_data)


def _handle_global_session_cmd(cmd: str, state: Dict[str, Any], log_data: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    lang = state["language"]
    parts = parse_command(cmd)
    if not parts:
        return state, log_data
    head = parts[0].lower()
    if head == "new":
        return _new_game_flow()
    if head == "list":
        _list_sessions(lang)
        return state, log_data
    if head == "load" and len(parts) == 2:
        pair = _load_session_cmd(parts[1], lang)
        if pair:
            return pair
        return state, log_data
    if head == "delete" and len(parts) == 2:
        ok = delete_session(parts[1])
        if ok:
            print(t("deleted", lang, sid=parts[1]))
        else:
            print(t("invalid_cmd", lang))
        return state, log_data
    return state, log_data


def _run_turn(state: Dict[str, Any], log_data: Dict[str, Any], action_text: str, dm_system: str) -> None:
    lang = state["language"]
    story = state["story"]
    story["turn"] += 1

    dm_context = _build_dm_context(state, log_data)
    raw_output = generate_dm_reply(dm_system, dm_context, action_text)
    narrative, directive = parse_dm_output(raw_output)
    turn_outcome = "neutral"

    print(f"[DM] {narrative}")
    offers = directive.get("offer_actions", [])
    if isinstance(offers, list) and offers:
        print("Actions:")
        for i, a in enumerate(offers[:4], start=1):
            print(f"{i}) {a}")
    append_event(log_data, "dm_narrative", narrative, {"raw": raw_output, "directive": directive})

    if directive.get("grant_clue"):
        clue = directive.get("clue", {})
        title = str(clue.get("title", "")).strip()
        detail = str(clue.get("detail", "")).strip()
        if title:
            _append_story_flag(story, f"clue:{title}")
        if detail:
            _append_story_flag(story, f"detail:{detail[:60]}")
        append_event(log_data, "update", "clue_granted", {"clue": clue})
    for flag in directive.get("flags_to_add", []):
        added = _append_story_flag(story, str(flag))
        if added:
            append_event(log_data, "update", "flag_added", {"flag": str(flag)})

    if directive.get("enter_combat"):
        pack_id = str(directive.get("combat", {}).get("enemy_pack_id", "")).strip() or "imp_pair"
        if not state.get("combat"):
            _start_combat_from_directive(state, pack_id)
            append_event(log_data, "combat", "combat_enter", {"enemy_pack_id": pack_id})

    if state.get("combat"):
        # Engine controls combat rolls and state changes, never the LLM.
        c = state["combat"]
        if directive.get("need_check"):
            attr = _directive_attr_to_internal(str(directive.get("check", {}).get("attribute", "Body")))
            dc = int(directive.get("check", {}).get("dc", 15))
        else:
            attr = "body"
            dc = 15

        bonus, mode = _consume_temp_effects(state["player"], attr, ["combat"])
        check = engine.resolve_check(
            stat=int(state["player"]["stats"][attr]),
            dc=dc,
            bonus=bonus,
            mode=mode,  # type: ignore[arg-type]
            use_passive=False,
        )
        outcome_key = engine.outcome(int(check["total"]), dc)
        append_event(
            log_data,
            "roll_result",
            "combat_check",
            {
                "attr": attr,
                "dc": dc,
                "mode": check["mode"],
                "rolls": check["rolls"],
                "d20": check["d20"],
                "mod": check["mod"],
                "bonus": check["bonus"],
                "total": check["total"],
                "outcome": outcome_key,
                "enemy_pack_id": c["enemy_pack_id"],
            },
        )
        print(t("roll_trigger", lang))
        attr_label = ATTR_LABEL[attr][lang]
        if lang == "zh":
            print(f"判定类型：主动（掷骰） | 属性：{attr_label}")
        else:
            print(f"Check Type: Active (rolled) | Attribute: {attr_label}")
        print(
            t(
                "roll_line",
                lang,
                d20=check["d20"],
                mod=check["mod"],
                bonus=check["bonus"],
                total=check["total"],
                dc=dc,
                outcome=t(outcome_key, lang),
            )
        )

        if outcome_key in {"outcome_critical", "outcome_success", "outcome_partial"}:
            dmg = engine.roll_d6(1) + max(0, int(state["player"]["mods"]["body"]))
            c["enemy_hp"] = max(0, int(c["enemy_hp"]) - dmg)
            append_event(log_data, "combat", "enemy_damaged", {"damage": dmg, "enemy_hp": c["enemy_hp"]})
        else:
            dmg = engine.roll_d6(1)
            state["player"]["hp"] = max(1, int(state["player"]["hp"]) - dmg)
            append_event(log_data, "combat", "player_damaged", {"damage": dmg, "hp": state["player"]["hp"]})

        c["round"] = int(c["round"]) + 1
        if int(c["enemy_hp"]) <= 0:
            append_event(log_data, "combat", "combat_win", {"enemy_pack_id": c["enemy_pack_id"], "round": c["round"]})
            story["progress"] += 1
            state["combat"] = None
        turn_outcome = outcome_key
    else:
        # Non-combat: directive decides key check vs passive resolution.
        if directive.get("need_check"):
            attr = _directive_attr_to_internal(str(directive.get("check", {}).get("attribute", "Mind")))
            dc = int(directive.get("check", {}).get("dc", 10))
            reason = str(directive.get("check", {}).get("reason", ""))
            bonus, mode = _consume_temp_effects(state["player"], attr, list(story.get("tags", [])))
            check = engine.resolve_check(
                stat=int(state["player"]["stats"][attr]),
                dc=dc,
                bonus=bonus,
                mode=mode,  # type: ignore[arg-type]
                use_passive=False,
            )
            outcome_key = engine.outcome(int(check["total"]), dc)
            append_event(
                log_data,
                "roll_result",
                "directive_check",
                {
                    "attr": attr,
                    "dc": dc,
                    "reason": reason,
                    "mode": check["mode"],
                    "rolls": check["rolls"],
                    "d20": check["d20"],
                    "mod": check["mod"],
                    "bonus": check["bonus"],
                    "total": check["total"],
                    "outcome": outcome_key,
                },
            )
            print(t("roll_trigger", lang))
            attr_label = ATTR_LABEL[attr][lang]
            if lang == "zh":
                print(f"判定类型：主动（掷骰） | 属性：{attr_label}")
            else:
                print(f"Check Type: Active (rolled) | Attribute: {attr_label}")
            print(
                t(
                    "roll_line",
                    lang,
                    d20=check["d20"],
                    mod=check["mod"],
                    bonus=check["bonus"],
                    total=check["total"],
                    dc=dc,
                    outcome=t(outcome_key, lang),
                )
            )
            status_key = _apply_outcome(
                state,
                log_data,
                {"id": "directive", "type": "clue", "risk": "high", "attr": attr, "dc": dc},
                check,
                outcome_key,
            )
            turn_outcome = outcome_key
        else:
            # Passive resolution path.
            attr = _directive_attr_to_internal(str(directive.get("check", {}).get("attribute", "Mind")))
            dc = int(directive.get("check", {}).get("dc", 10))
            check = engine.resolve_check(
                stat=int(state["player"]["stats"][attr]),
                dc=dc,
                bonus=0,
                mode="normal",
                use_passive=True,
            )
            outcome_key = engine.outcome(int(check["total"]), dc)
            append_event(
                log_data,
                "roll_result",
                "directive_passive",
                {
                    "attr": attr,
                    "dc": dc,
                    "total": check["total"],
                    "passive": True,
                    "outcome": outcome_key,
                },
            )
            status_key = "passive_success" if check["success"] else "passive_fail"
            turn_outcome = status_key
            attr_label = ATTR_LABEL[attr][lang]
            if lang == "zh":
                print(f"判定类型：被动（不掷骰） | 属性：{attr_label}")
                print(f"被动值计算：10 + mod({check['mod']}) + bonus({check['bonus']}) = {check['total']} vs DC{dc}")
            else:
                print(f"Check Type: Passive (no roll) | Attribute: {attr_label}")
                print(f"Passive Calc: 10 + mod({check['mod']}) + bonus({check['bonus']}) = {check['total']} vs DC{dc}")
            print(t(status_key, lang))
            if check["success"]:
                story["progress"] += 1
            else:
                story["threat_level"] += 1
        append_event(log_data, "scene", "turn_resolved", {"status_key": status_key})

    _apply_npc_attitude_changes(
        state,
        log_data,
        directive.get("npc_attitude_changes", []) if isinstance(directive.get("npc_attitude_changes", []), list) else [],
    )
    _run_world_tick(state, log_data, directive, turn_outcome)

    completed_reward = _check_quest_completion(state, log_data)
    if completed_reward is not None:
        print(t("quest_complete", lang, gold=completed_reward))
    save_session(state, log_data)


def run_game_loop(state: Dict[str, Any], log_data: Dict[str, Any]) -> None:
    dm_system = _read_dm_system()
    if state.get("seed") is not None:
        engine.set_seed(int(state["seed"]))
    else:
        engine.set_seed(None)

    if not is_online_available():
        print("当前离线模式")

    while True:
        lang = state["language"]
        print_hud(state)
        raw = _ask(t("turn_prompt", lang))
        if not raw:
            continue
        if raw.lower() in QUIT_WORDS:
            append_event(log_data, "update", "session_exit", {})
            save_session(state, log_data)
            print(t("exit", lang))
            break
        if _pick_language_from_cmd(state, log_data, raw):
            continue
        if _pick_seed(state, log_data, raw):
            continue

        parts = parse_command(raw)
        head = parts[0].lower() if parts else ""

        if head in {"new", "list", "load", "delete"}:
            pair = _handle_global_session_cmd(raw, state, log_data)
            if pair is None:
                continue
            state, log_data = pair
            _ensure_runtime_fields(state)
            save_session(state, log_data)
            continue
        if head == "inv":
            print_inventory(state)
            continue
        if head == "shop":
            print_shop(state)
            continue
        if head == "buy" and len(parts) >= 2:
            qty = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
            _buy_item(state, log_data, parts[1], qty)
            continue
        if head == "use" and len(parts) == 2:
            _use_item(state, log_data, parts[1])
            continue

        append_event(log_data, "action", raw, {})
        _run_turn(state, log_data, raw, dm_system)


def main() -> None:
    ensure_dirs()
    sid = get_current_session_id()
    loaded: Optional[Tuple[Dict[str, Any], Dict[str, Any]]] = None
    if sid:
        loaded = load_session(sid)
    if not loaded:
        clear_current_session_id()
        loaded = _boot_menu()
        if loaded is None:
            return
    state, log_data = loaded
    _ensure_runtime_fields(state)
    set_current_session_id(state["session_id"])
    save_session(state, log_data)
    run_game_loop(state, log_data)


if __name__ == "__main__":
    main()
