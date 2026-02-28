from __future__ import annotations

from typing import Any, Dict, Tuple

from xiyou_solo.infra.session_store import DATA_DIR, GameSessionStore, read_json, write_json
from xiyou_solo.ui.bot_runner import create_bot_session, run_turn, run_utility_command


TG_MAP_PATH = DATA_DIR / "telegram_map.json"
ONBOARD_STAGES = {"choose_language", "input_api_key", "choose_scenario", "create_character", "playing"}

SCENARIOS: Dict[str, Dict[str, Dict[str, str]]] = {
    "huangfeng": {
        "title": {"zh": "黄风岭迷雾", "en": "Mist of Huangfeng Ridge"},
        "goal": {"zh": "找出真路并护送药材通过山口", "en": "Find the true route and escort medicine through the pass"},
        "location": {"zh": "黄风岭前哨", "en": "Huangfeng Outpost"},
    },
    "baigu": {
        "title": {"zh": "白骨疑影", "en": "Shadows at White Bone Ridge"},
        "goal": {"zh": "辨明身份并避免误伤无辜", "en": "Identify the truth and avoid harming innocents"},
        "location": {"zh": "白骨岭驿站", "en": "White Bone Ridge Post"},
    },
    "huoyan": {
        "title": {"zh": "火焰山借扇", "en": "Borrow the Fan at Flame Mountain"},
        "goal": {"zh": "借来宝扇缓解热浪", "en": "Borrow the fan to ease the heatwave"},
        "location": {"zh": "火焰山脚", "en": "Foot of Flame Mountain"},
    },
}

SCENARIO_ORDER = ["huangfeng", "baigu", "huoyan"]


def load_map() -> Dict[str, str]:
    raw = read_json(TG_MAP_PATH, {})
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def save_map(chat_map: Dict[str, str]) -> None:
    write_json(TG_MAP_PATH, chat_map)


def _default_onboarding() -> Dict[str, Any]:
    return {
        "stage": "choose_language",
        "language": "zh",
        "api_key": "",
        "scenario_id": "",
        "character_name": "",
    }


def _ensure_onboarding_meta(meta: Dict[str, Any], *, force_reset: bool = False) -> Dict[str, Any]:
    out = dict(meta)
    if force_reset or not isinstance(out.get("onboarding"), dict):
        out["onboarding"] = _default_onboarding()
    ob = dict(out.get("onboarding", {}))
    if force_reset:
        ob = _default_onboarding()
    ob.setdefault("stage", "choose_language")
    if str(ob.get("stage", "")) not in ONBOARD_STAGES:
        ob["stage"] = "choose_language"
    ob.setdefault("language", "zh")
    if str(ob["language"]) not in {"zh", "en"}:
        ob["language"] = "zh"
    ob.setdefault("api_key", "")
    ob.setdefault("scenario_id", "")
    ob.setdefault("character_name", "")
    out["onboarding"] = ob
    return out


def _language_prompt() -> str:
    return "请选择语言 / Choose language:\n- 输入 zh\n- 输入 en"


def _api_key_prompt(lang: str) -> str:
    if lang == "en":
        return "Please send your OpenRouter API key (starts with sk-), or send /skip to use server default."
    return "请发送你的 OpenRouter API Key（以 sk- 开头），或发送 /skip 使用服务器默认 key。"


def _scenario_prompt(lang: str) -> str:
    if lang == "en":
        return (
            "Choose scenario:\n"
            "1) Mist of Huangfeng Ridge\n"
            "2) Shadows at White Bone Ridge\n"
            "3) Borrow the Fan at Flame Mountain\n"
            "Reply with 1/2/3."
        )
    return (
        "请选择副本：\n"
        "1) 黄风岭迷雾\n"
        "2) 白骨疑影\n"
        "3) 火焰山借扇\n"
        "回复 1/2/3。"
    )


def _character_prompt(lang: str) -> str:
    if lang == "en":
        return "Create your character: reply with a character name."
    return "创建角色：请回复角色名。"


def _parse_language(raw: str) -> str | None:
    txt = raw.strip().lower()
    if txt.startswith("/lang "):
        txt = txt.split(maxsplit=1)[1].strip().lower()
    if txt in {"zh", "en"}:
        return txt
    return None


def _parse_scenario(raw: str) -> str | None:
    txt = raw.strip().lower()
    mapping = {"1": SCENARIO_ORDER[0], "2": SCENARIO_ORDER[1], "3": SCENARIO_ORDER[2]}
    if txt in mapping:
        return mapping[txt]
    if txt in SCENARIOS:
        return txt
    return None


def _mask_key(v: str) -> str:
    s = (v or "").strip()
    if len(s) <= 8:
        return "***"
    return f"{s[:6]}...{s[-4:]}"


def _is_api_key_like(raw: str) -> bool:
    s = raw.strip()
    return (s.startswith("sk-or-") or s.startswith("sk-")) and len(s) >= 20


def _init_session_for_chat(chat_id: int, *, force_new: bool) -> Tuple[str, bool]:
    chat_key = str(chat_id)
    chat_map = load_map()
    sid = chat_map.get(chat_key, "")
    store = GameSessionStore()

    if force_new or not sid:
        sid = store.create_session(
            player_id=f"telegram:{chat_key}",
            meta={"source": "telegram", "created_by": "services.tg_handler"},
        )
        create_bot_session(sid, language="zh", player_name=f"tg_{chat_key}")
        meta = _ensure_onboarding_meta(store.load_meta(sid), force_reset=True)
        store.save_meta(sid, meta)
        chat_map[chat_key] = sid
        save_map(chat_map)
        return sid, True

    if not store.load_game(sid):
        create_bot_session(sid, language="zh", player_name=f"tg_{chat_key}")
    meta = _ensure_onboarding_meta(store.load_meta(sid), force_reset=False)
    store.save_meta(sid, meta)
    return sid, False


def _format_actions(directive: Dict[str, Any]) -> str:
    actions = directive.get("offer_actions", [])
    if not isinstance(actions, list) or not actions:
        return ""
    lines = ["\nActions:"]
    for idx, text in enumerate(actions[:5], start=1):
        lines.append(f"{idx}. {text}")
    return "\n".join(lines)


def format_reply(narrative: str, directive: Dict[str, Any], state_summary: str) -> str:
    txt = narrative.strip()
    action_block = _format_actions(directive)
    if action_block:
        txt = f"{txt}\n{action_block}"
    if state_summary.strip():
        txt = f"{txt}\n\n{state_summary.strip()}"
    return txt.strip()


def _handle_onboarding(chat_id: int, sid: str, raw: str) -> str:
    store = GameSessionStore()
    loaded = store.load_game(sid)
    if not loaded:
        create_bot_session(sid, language="zh", player_name=f"tg_{chat_id}")
        loaded = store.load_game(sid)
    if not loaded:
        return "Failed to initialize session."
    state, log_data = loaded

    meta = _ensure_onboarding_meta(store.load_meta(sid), force_reset=False)
    ob = meta["onboarding"]
    stage = str(ob.get("stage", "choose_language"))
    lang = str(ob.get("language", "zh"))

    if stage == "choose_language":
        picked = _parse_language(raw)
        if not picked:
            return _language_prompt()
        ob["language"] = picked
        ob["stage"] = "input_api_key"
        state.language = picked
        store.save_game(state, log_data)
        store.save_meta(sid, meta)
        return _api_key_prompt(picked)

    if stage == "input_api_key":
        txt = raw.strip()
        if txt.lower() == "/skip":
            ob["api_key"] = ""
            ob["stage"] = "choose_scenario"
            store.save_meta(sid, meta)
            return _scenario_prompt(lang)
        if not _is_api_key_like(txt):
            if lang == "en":
                return "Invalid key format. Please send a key starting with sk-, or /skip."
            return "Key 格式不对，请发送以 sk- 开头的 key，或发送 /skip。"
        ob["api_key"] = txt
        ob["stage"] = "choose_scenario"
        store.save_meta(sid, meta)
        if lang == "en":
            return f"API key saved ({_mask_key(txt)}).\n\n{_scenario_prompt(lang)}"
        return f"已保存 API key（{_mask_key(txt)}）。\n\n{_scenario_prompt(lang)}"

    if stage == "choose_scenario":
        sid_choice = _parse_scenario(raw)
        if not sid_choice:
            return _scenario_prompt(lang)
        sc = SCENARIOS[sid_choice]
        state.quest_title = dict(sc["title"])
        state.current_goal = dict(sc["goal"])
        state.location = dict(sc["location"])
        state.progress = 0
        state.threat_level = 1
        ob["scenario_id"] = sid_choice
        ob["stage"] = "create_character"
        store.save_game(state, log_data)
        store.save_meta(sid, meta)
        return _character_prompt(lang)

    if stage == "create_character":
        name = raw.strip()
        if not name:
            return _character_prompt(lang)
        state.player_name = name[:24]
        ob["character_name"] = state.player_name
        ob["stage"] = "playing"
        store.save_game(state, log_data)
        store.save_meta(sid, meta)
        if lang == "en":
            return f"Character created: {state.player_name}\n\n{run_utility_command(sid, 'status')}"
        return f"角色创建完成：{state.player_name}\n\n{run_utility_command(sid, 'status')}"

    return run_utility_command(sid, "status")


def handle_chat_text(chat_id: int, text: str) -> str:
    raw = (text or "").strip()
    sid, _ = _init_session_for_chat(chat_id, force_new=False)

    if not raw:
        return "Send /start to begin onboarding, or /help for commands."

    if raw.startswith("/"):
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in {"/start", "/new"}:
            sid, _ = _init_session_for_chat(chat_id, force_new=True)
            return _language_prompt()
        if cmd == "/help":
            return (
                "Commands:\n"
                "/start - start onboarding\n"
                "/new - create a new session and restart onboarding\n"
                "/status - show current status\n"
                "/inv - inventory\n"
                "/shop - shop list\n"
                "/buy <item_id> [qty]\n"
                "/use <item_id>\n"
                "/lang zh|en\n"
                "/skip - skip API key step during onboarding"
            )
        if cmd == "/status":
            return run_utility_command(sid, "status")
        if cmd == "/inv":
            return run_utility_command(sid, "inv")
        if cmd == "/shop":
            return run_utility_command(sid, "shop")
        if cmd == "/buy":
            return run_utility_command(sid, f"buy {arg}".strip())
        if cmd == "/use":
            return run_utility_command(sid, f"use {arg}".strip())
        if cmd == "/lang":
            return run_utility_command(sid, f"lang {arg}".strip())
        if cmd == "/skip":
            # Only meaningful during onboarding API-key stage.
            return _handle_onboarding(chat_id, sid, "/skip")
        return "Unknown command. Use /help."

    store = GameSessionStore()
    meta = _ensure_onboarding_meta(store.load_meta(sid), force_reset=False)
    stage = str(meta.get("onboarding", {}).get("stage", "choose_language"))
    if stage != "playing":
        reply = _handle_onboarding(chat_id, sid, raw)
        meta2 = _ensure_onboarding_meta(store.load_meta(sid), force_reset=False)
        if str(meta2.get("onboarding", {}).get("stage", "choose_language")) != "playing":
            return reply

    meta = _ensure_onboarding_meta(store.load_meta(sid), force_reset=False)
    api_key = str(meta.get("onboarding", {}).get("api_key", "")).strip() or None
    narrative, directive, state_summary = run_turn(sid, raw, api_key=api_key)
    return format_reply(narrative, directive, state_summary)
