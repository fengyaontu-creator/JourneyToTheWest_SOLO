from __future__ import annotations

from typing import Any, Dict, List


ATTRS = ("body", "wit", "spirit", "luck")
ATTR_LABEL = {
    "body": {"zh": "体", "en": "Body"},
    "wit": {"zh": "智", "en": "Wit"},
    "spirit": {"zh": "心", "en": "Spirit"},
    "luck": {"zh": "运", "en": "Luck"},
}


RACES: Dict[str, Dict[str, Any]] = {
    "human": {
        "name": {"zh": "人族", "en": "Human"},
        "desc": {"zh": "适应力强，开局更富有。", "en": "Adaptable and starts richer."},
        "stat_bonus": {"body": 0, "wit": 0, "spirit": 0, "luck": 0},
        "creation_bonus_pick_two": 1,
        "starting_gold_bonus": 20,
        "talent": {"id": "adaptable", "name": {"zh": "应变", "en": "Adaptable"}, "desc": {"zh": "每场首次失败检定可重掷", "en": "Reroll first failed check each adventure"}},
    },
    "fox_spirit": {
        "name": {"zh": "妖族·狐灵", "en": "Fox Spirit"},
        "desc": {"zh": "擅社交与欺瞒。", "en": "Excels at social deception."},
        "stat_bonus": {"body": 0, "wit": 2, "spirit": 0, "luck": 1},
        "starting_gold_bonus": 0,
        "talent": {"id": "glamour", "name": {"zh": "惑形", "en": "Glamour"}, "desc": {"zh": "社交检定每日2次优势", "en": "Advantage on social checks 2/day"}},
    },
    "mountain_sprite": {
        "name": {"zh": "妖族·山精", "en": "Mountain Sprite"},
        "desc": {"zh": "体魄厚实，耐打耐爬。", "en": "Sturdy and resilient."},
        "stat_bonus": {"body": 2, "wit": 0, "spirit": 1, "luck": 0},
        "starting_gold_bonus": 0,
        "talent": {"id": "stone_endurance", "name": {"zh": "磐石韧性", "en": "Stone Endurance"}, "desc": {"zh": "每场一次减伤1d6+体修正", "en": "Reduce damage by 1d6+Body mod once per adventure"}},
    },
    "dragonkin": {
        "name": {"zh": "龙裔", "en": "Dragonkin"},
        "desc": {"zh": "意志强，具龙息。", "en": "Strong will with draconic breath."},
        "stat_bonus": {"body": 1, "wit": 0, "spirit": 2, "luck": 0},
        "starting_gold_bonus": 0,
        "talent": {"id": "dragon_breath", "name": {"zh": "龙息", "en": "Dragon Breath"}, "desc": {"zh": "每场一次2d6伤害或逼退", "en": "2d6 damage or push once per adventure"}},
    },
    "spirit_born": {
        "name": {"zh": "灵修", "en": "Spirit-Born"},
        "desc": {"zh": "灵性强，受吉兆庇护。", "en": "Spirit-attuned and omen-blessed."},
        "stat_bonus": {"body": 0, "wit": 0, "spirit": 2, "luck": 1},
        "starting_gold_bonus": 0,
        "talent": {"id": "auspice", "name": {"zh": "吉兆", "en": "Auspice"}, "desc": {"zh": "每场一次掷后+2", "en": "+2 after a d20 roll once per adventure"}},
    },
}


CLASSES: Dict[str, Dict[str, Any]] = {
    "martial": {
        "name": {"zh": "武行者", "en": "Martial"},
        "desc": {"zh": "擅长正面冲突。", "en": "Frontline combat specialist."},
        "core_attr": "body",
        "starter_items": ["dagger", "simple_armor"],
        "resources": {"power_strike": 2},
    },
    "pilgrim_monk": {
        "name": {"zh": "行脚僧", "en": "Pilgrim Monk"},
        "desc": {"zh": "稳住局面，擅长心性。", "en": "Stable support focused on spirit."},
        "core_attr": "spirit",
        "starter_items": ["healing_herbs", "incense_charm"],
        "resources": {"calm_mind": 2},
    },
    "talismanist": {
        "name": {"zh": "方士", "en": "Talismanist"},
        "desc": {"zh": "调查与符法专精。", "en": "Investigation and talisman specialist."},
        "core_attr": "wit",
        "starter_items": ["torch", "mirror_token", "travel_rations"],
        "resources": {"talisman": 3},
    },
    "wanderer": {
        "name": {"zh": "游侠", "en": "Wanderer"},
        "desc": {"zh": "机动与追踪能力强。", "en": "Mobile pathfinder and tracker."},
        "core_attr": "luck",
        "starter_items": ["rope", "shard_shot", "travel_rations"],
        "resources": {"lucky_move": 2},
    },
}


ITEMS: Dict[str, Dict[str, Any]] = {
    "healing_herbs": {"name": {"zh": "草药包", "en": "Healing Herbs"}, "desc": {"zh": "回复1d6+2 HP", "en": "Recover 1d6+2 HP"}, "price": 25, "effect": {"type": "heal", "dice": [1, 6], "bonus": 2}},
    "incense_charm": {"name": {"zh": "清心香囊", "en": "Incense Charm"}, "desc": {"zh": "下一次心检定+2", "en": "Next Spirit check +2"}, "price": 20, "effect": {"type": "next_bonus", "attr": "spirit", "bonus": 2}},
    "torch": {"name": {"zh": "火把", "en": "Torch"}, "desc": {"zh": "迷雾场景信息优势", "en": "Info advantage in mist scenes"}, "price": 5, "effect": {"type": "next_advantage", "tags": ["mist"]}},
    "rope": {"name": {"zh": "麻绳", "en": "Rope"}, "desc": {"zh": "攀爬/束缚体检定+1", "en": "+1 Body for climb/bind checks"}, "price": 8, "effect": {"type": "next_bonus", "attr": "body", "bonus": 1}},
    "mirror_token": {"name": {"zh": "照妖镜片", "en": "Mirror Token"}, "desc": {"zh": "识破伪装，智检定优势1次", "en": "Advantage on one disguise/illusion Wit check"}, "price": 30, "effect": {"type": "next_advantage", "tags": ["identity", "illusion"]}},
    "travel_rations": {"name": {"zh": "干粮", "en": "Travel Rations"}, "desc": {"zh": "下一次体检定+1", "en": "+1 to next Body check"}, "price": 6, "effect": {"type": "next_bonus", "attr": "body", "bonus": 1}},
    "simple_armor": {"name": {"zh": "轻甲", "en": "Simple Armor"}, "desc": {"zh": "HP上限+2（首次装备时）", "en": "HP max +2 on first equip"}, "price": 40, "effect": {"type": "max_hp_once", "bonus": 2}},
    "shard_shot": {"name": {"zh": "碎石弹", "en": "Shard Shot"}, "desc": {"zh": "一次性，造成1d6伤害", "en": "Single-use 1d6 damage"}, "price": 12, "effect": {"type": "damage_item", "dice": [1, 6]}},
    "dagger": {"name": {"zh": "匕首", "en": "Dagger"}, "desc": {"zh": "基础近战武器", "en": "Basic melee weapon"}, "price": 15, "effect": {"type": "passive"}},
}


QUESTS: Dict[str, Dict[str, Any]] = {
    "huangfeng_mist": {
        "title": {"zh": "黄风岭迷雾", "en": "Huangfeng Mist"},
        "hook": {"zh": "商队在黄风岭迷失，真假路标混杂。", "en": "A caravan is lost among false signs in Huangfeng Ridge."},
        "goal": {"zh": "找出真路并护送药材通过山口。", "en": "Find the true route and escort the medicine cargo through the pass."},
        "reward_gold_range": [60, 120],
        "tags": ["mist", "sand", "mislead"],
        "start_location": {"zh": "黄风岭前哨", "en": "Huangfeng Outpost"},
    },
    "whitebone_shadow": {
        "title": {"zh": "白骨疑影", "en": "Whitebone Doubt"},
        "hook": {"zh": "村中来客身份可疑，误判可能惹大祸。", "en": "A suspicious visitor appears; misjudgment could be costly."},
        "goal": {"zh": "辨明身份并避免误伤无辜。", "en": "Identify the true threat without harming innocents."},
        "reward_gold_range": [70, 130],
        "tags": ["identity", "social", "illusion"],
        "start_location": {"zh": "白骨岭驿站", "en": "Whitebone Posthouse"},
    },
    "flame_mountain_fan": {
        "title": {"zh": "火焰山借扇", "en": "Fan for Flame Mountain"},
        "hook": {"zh": "热浪逼城，需借来宝扇缓解灾情。", "en": "Heatwaves threaten the town; you must borrow a sacred fan."},
        "goal": {"zh": "在高温压力下谈成借扇条件。", "en": "Negotiate terms for the fan under severe heat pressure."},
        "reward_gold_range": [80, 140],
        "tags": ["heat", "social", "pressure"],
        "start_location": {"zh": "火焰山脚集市", "en": "Flamefoot Bazaar"},
    },
    "queendom_incident": {
        "title": {"zh": "女儿国风波", "en": "Queendom Stir"},
        "hook": {"zh": "庆典前夕流言四起，需化解误会。", "en": "Rumors spread before a festival; tensions need easing."},
        "goal": {"zh": "平息风波并保住庆典顺利举行。", "en": "Defuse conflict and keep the festival running."},
        "reward_gold_range": [50, 110],
        "tags": ["social", "etiquette", "mislead"],
        "start_location": {"zh": "女儿国外城", "en": "Queendom Outer City"},
    },
}


# Quest tag -> possible runtime event templates.
EVENT_POOL: Dict[str, List[Dict[str, Any]]] = {
    "mist": [
        {"id": "mist_path", "type": "clue", "title": {"zh": "雾中岔路", "en": "Fork in the Mist"}, "risk": "low", "attr": "wit", "dc": 12},
        {"id": "mist_ambush", "type": "hazard", "title": {"zh": "雾中伏击", "en": "Ambush in Fog"}, "risk": "high", "attr": "body", "dc": 15},
    ],
    "sand": [
        {"id": "sand_blast", "type": "hazard", "title": {"zh": "风沙突袭", "en": "Sand Burst"}, "risk": "high", "attr": "body", "dc": 14},
        {"id": "sand_clue", "type": "clue", "title": {"zh": "残迹浮现", "en": "Trace Emerges"}, "risk": "low", "attr": "wit", "dc": 11},
    ],
    "identity": [
        {"id": "identity_test", "type": "clue", "title": {"zh": "身份盘问", "en": "Identity Probe"}, "risk": "high", "attr": "spirit", "dc": 15},
        {"id": "identity_hint", "type": "clue", "title": {"zh": "细节破绽", "en": "Minor Inconsistency"}, "risk": "low", "attr": "wit", "dc": 12},
    ],
    "social": [
        {"id": "social_talk", "type": "clue", "title": {"zh": "街谈巷议", "en": "Street Talk"}, "risk": "low", "attr": "spirit", "dc": 12},
        {"id": "social_conflict", "type": "hazard", "title": {"zh": "口角升级", "en": "Escalating Argument"}, "risk": "high", "attr": "spirit", "dc": 15},
    ],
    "heat": [
        {"id": "heat_wave", "type": "hazard", "title": {"zh": "热浪压顶", "en": "Crushing Heatwave"}, "risk": "high", "attr": "body", "dc": 15},
        {"id": "heat_rest", "type": "reward", "title": {"zh": "阴凉补给", "en": "Shade Supply"}, "risk": "low", "attr": "luck", "dc": 10},
    ],
    "mislead": [
        {"id": "false_clue", "type": "mislead", "title": {"zh": "假线索", "en": "False Lead"}, "risk": "low", "attr": "wit", "dc": 12},
        {"id": "trickster", "type": "hazard", "title": {"zh": "小妖戏弄", "en": "Imp Trick"}, "risk": "high", "attr": "luck", "dc": 14},
    ],
    "pressure": [
        {"id": "time_limit", "type": "hazard", "title": {"zh": "时限逼近", "en": "Deadline Closing"}, "risk": "high", "attr": "spirit", "dc": 16}
    ],
    "etiquette": [
        {"id": "etiquette_test", "type": "clue", "title": {"zh": "礼仪试探", "en": "Etiquette Test"}, "risk": "low", "attr": "spirit", "dc": 12}
    ],
}

