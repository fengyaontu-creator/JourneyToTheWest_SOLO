from __future__ import annotations

from typing import Any, Dict


TEXTS: Dict[str, Dict[str, str]] = {
    "title": {"zh": "西游 Solo TRPG v0.4", "en": "Journey Solo TRPG v0.4"},
    "boot_hint": {"zh": "命令：new | list | load <id> | delete <id> | quit", "en": "Commands: new | list | load <id> | delete <id> | quit"},
    "no_session": {"zh": "当前没有已加载存档。", "en": "No active session loaded."},
    "new_start": {"zh": "开始新冒险。", "en": "Starting a new adventure."},
    "input_name": {"zh": "输入角色名：", "en": "Enter character name: "},
    "pick_quest": {"zh": "选择任务（1-4 或 random）：", "en": "Pick quest (1-4 or random): "},
    "pick_race": {"zh": "选择种族编号：", "en": "Pick race number: "},
    "pick_class": {"zh": "选择职业编号：", "en": "Pick class number: "},
    "pick_roll_method": {"zh": "属性生成方式：1)3d6 2)4d6去最低（默认1）> ", "en": "Stat method: 1)3d6 2)4d6 drop lowest (default 1) > "},
    "turn_prompt": {"zh": "你要做什么？> ", "en": "What do you do? > "},
    "lang_usage": {"zh": "用法：lang zh|en", "en": "Usage: lang zh|en"},
    "lang_switched": {"zh": "语言已切换为中文。", "en": "Language switched to English."},
    "seed_set": {"zh": "随机种子已设置为 {seed}", "en": "Random seed set to {seed}"},
    "invalid_cmd": {"zh": "无法识别命令。", "en": "Unknown command."},
    "hud_line": {"zh": "任务：{quest} | 目标：{goal} | 地点：{location}", "en": "Quest: {quest} | Goal: {goal} | Location: {location}"},
    "hud_line2": {"zh": "HP {hp}/{max_hp} | 金币 {gold} | 关键道具 {items}", "en": "HP {hp}/{max_hp} | Gold {gold} | Key Items {items}"},
    "passive_success": {"zh": "被动通过：你稳定处理了这个环节。", "en": "Passive success: you handle it steadily."},
    "passive_fail": {"zh": "被动失败：需要更强手段。", "en": "Passive fail: stronger action needed."},
    "roll_trigger": {"zh": "触发关键检定。", "en": "Key check triggered."},
    "outcome_critical": {"zh": "超额成功", "en": "Great Success"},
    "outcome_success": {"zh": "成功", "en": "Success"},
    "outcome_partial": {"zh": "代价成功", "en": "Success with Cost"},
    "outcome_fail": {"zh": "失败", "en": "Failure"},
    "outcome_fumble": {"zh": "大失败", "en": "Critical Failure"},
    "quest_complete": {"zh": "任务完成！获得金币 +{gold}", "en": "Quest complete! Gold +{gold}"},
    "inventory_title": {"zh": "背包与状态", "en": "Inventory & Status"},
    "inventory_items": {"zh": "道具：{items}", "en": "Items: {items}"},
    "inventory_gold": {"zh": "金币：{gold}", "en": "Gold: {gold}"},
    "shop_title": {"zh": "商店", "en": "Shop"},
    "buy_ok": {"zh": "购买成功：{item} x{qty}，花费 {cost}", "en": "Purchased: {item} x{qty}, spent {cost}"},
    "buy_no_money": {"zh": "金币不足。", "en": "Not enough gold."},
    "use_ok": {"zh": "使用道具：{item}", "en": "Used item: {item}"},
    "use_missing": {"zh": "背包没有该道具：{item_id}", "en": "Item not in inventory: {item_id}"},
    "roll_line": {"zh": "检定：d20={d20} mod={mod} bonus={bonus} total={total} vs DC{dc} -> {outcome}", "en": "Check: d20={d20} mod={mod} bonus={bonus} total={total} vs DC{dc} -> {outcome}"},
    "saved": {"zh": "已保存。", "en": "Saved."},
    "loaded": {"zh": "已加载：{sid}", "en": "Loaded: {sid}"},
    "deleted": {"zh": "已删除：{sid}", "en": "Deleted: {sid}"},
    "list_none": {"zh": "没有可用存档。", "en": "No sessions found."},
    "list_title": {"zh": "存档列表：", "en": "Sessions:"},
    "exit": {"zh": "已退出。", "en": "Bye."},
}


def t(key: str, lang: str, **kwargs: Any) -> str:
    table = TEXTS.get(key, {})
    text = table.get(lang) or table.get("zh") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

