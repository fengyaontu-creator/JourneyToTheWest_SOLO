from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from xiyou_solo.infra.session_store import make_session_id

from . import room_repo


TurnExecutor = Callable[[str, str, str, Dict[str, Any]], str]


def _help_text() -> str:
    return (
        "Commands: /new /join /start /end /pick <role> /me /party /act <text> "
        "/pass /next /pause /resume"
    )


def _parse_cmd(text: str) -> tuple[str, str]:
    raw = (text or "").strip()
    if not raw:
        return "", ""
    if not raw.startswith("/"):
        return "act", raw
    parts = raw.split(maxsplit=1)
    cmd = parts[0][1:].strip().lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return cmd, arg


def _room_summary(group_id: str, data: Dict[str, Any]) -> str:
    room = room_repo.get_room(data, group_id)
    if not room:
        return "No active room. Use /new first."
    room = room_repo.ensure_room_shape(group_id, room)
    binds = room_repo.list_group_bindings(data, group_id)
    players = ", ".join([f"{uid}:{v.get('role_name', '')}" for uid, v in binds.items()]) or "(none)"
    return (
        f"Room={room.get('session_id','')} status={room.get('status','waiting')} "
        f"turn={room.get('current_turn_user_id','')} players={players}"
    )


def handle_message(
    group_id: str,
    user_id: str,
    text: str,
    message_id: str,
    turn_executor: Optional[TurnExecutor] = None,
    now_ts: Optional[float] = None,
    min_interval_sec: float = 0.0,
) -> List[str]:
    """
    Message entry for adapters (wechat/telegram/discord).

    turn_executor receives: session_id, user_id, action_text, metadata
    and should return text reply for group broadcast.
    """
    ts = float(now_ts if now_ts is not None else time.time())
    data = room_repo.load_rooms()
    replies: List[str] = []
    dedup_id = f"{group_id}:{message_id}" if message_id else ""

    if dedup_id and room_repo.is_processed(data, dedup_id):
        return ["Duplicate message ignored."]

    last_ts = room_repo.get_rate_limit_ts(data, group_id, user_id)
    if min_interval_sec > 0 and ts - last_ts < float(min_interval_sec):
        return ["Too many commands. Please wait a moment."]
    room_repo.set_rate_limit_ts(data, group_id, user_id, ts)

    cmd, arg = _parse_cmd(text)
    if not cmd:
        room_repo.mark_processed(data, dedup_id)
        room_repo.save_rooms(data)
        return [_help_text()]

    room = room_repo.get_room(data, group_id)

    if cmd == "new":
        sid = make_session_id()
        room = {
            "group_id": group_id,
            "session_id": sid,
            "host_user_id": user_id,
            "turn_order": [user_id],
            "current_turn_user_id": user_id,
            "status": "waiting",
        }
        room_repo.set_room(data, group_id, room)
        room_repo.bind_player(data, group_id, user_id, "host")
        replies.append(f"Room created. session={sid}. Others can /join.")

    elif cmd == "join":
        if not room:
            replies.append("No active room. Use /new first.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if user_id not in room["turn_order"]:
                room["turn_order"].append(user_id)
            if not room_repo.get_binding(data, group_id, user_id):
                room_repo.bind_player(data, group_id, user_id, "")
            room_repo.set_room(data, group_id, room)
            replies.append(f"{user_id} joined.")

    elif cmd == "pick":
        if not room:
            replies.append("No active room. Use /new first.")
        elif not arg:
            replies.append("Usage: /pick <role_name>")
        else:
            room_repo.bind_player(data, group_id, user_id, arg[:32])
            replies.append(f"{user_id} role set to {arg[:32]}.")

    elif cmd == "start":
        if not room:
            replies.append("No active room. Use /new first.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if room["host_user_id"] != user_id:
                replies.append("Only host can /start.")
            else:
                room["status"] = "running"
                if not room.get("current_turn_user_id"):
                    room["current_turn_user_id"] = room["turn_order"][0] if room["turn_order"] else ""
                room_repo.set_room(data, group_id, room)
                replies.append(f"Game started. Current turn: {room['current_turn_user_id']}")

    elif cmd == "end":
        if not room:
            replies.append("No active room.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if room["host_user_id"] != user_id:
                replies.append("Only host can /end.")
            else:
                room_repo.remove_room(data, group_id)
                replies.append("Room ended.")

    elif cmd in {"me", "party"}:
        replies.append(_room_summary(group_id, data))

    elif cmd == "pause":
        if not room:
            replies.append("No active room.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if room["host_user_id"] != user_id:
                replies.append("Only host can /pause.")
            else:
                room["status"] = "paused"
                room_repo.set_room(data, group_id, room)
                replies.append("Game paused.")

    elif cmd == "resume":
        if not room:
            replies.append("No active room.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if room["host_user_id"] != user_id:
                replies.append("Only host can /resume.")
            else:
                room["status"] = "running"
                room_repo.set_room(data, group_id, room)
                replies.append("Game resumed.")

    elif cmd in {"next", "pass"}:
        if not room:
            replies.append("No active room.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if cmd == "next" and room["host_user_id"] != user_id:
                replies.append("Only host can /next.")
            elif cmd == "pass" and room.get("current_turn_user_id") != user_id:
                replies.append("Not your turn.")
            else:
                nxt = room_repo.next_turn_user(room)
                room_repo.set_room(data, group_id, room)
                replies.append(f"Turn advanced. Current turn: {nxt}")

    elif cmd == "act":
        if not room:
            replies.append("No active room. Use /new first.")
        else:
            room = room_repo.ensure_room_shape(group_id, room)
            if room.get("status") != "running":
                replies.append("Game is not running. Use /start.")
            elif room.get("current_turn_user_id") != user_id:
                replies.append("Not your turn.")
            elif not arg:
                replies.append("Usage: /act <your action text>")
            else:
                sid = str(room.get("session_id", "")).strip()
                if turn_executor is None:
                    replies.append(f"[stub] action accepted for session={sid}: {arg}")
                else:
                    try:
                        reply = turn_executor(sid, user_id, arg, {"group_id": group_id, "message_id": message_id})
                        replies.append(reply)
                    except Exception as exc:  # pragma: no cover
                        replies.append(f"Action failed: {exc}")
                nxt = room_repo.next_turn_user(room)
                room_repo.set_room(data, group_id, room)
                replies.append(f"Next turn: {nxt}")

    else:
        replies.append(_help_text())

    if dedup_id:
        room_repo.mark_processed(data, dedup_id)
    room_repo.save_rooms(data)
    return replies
