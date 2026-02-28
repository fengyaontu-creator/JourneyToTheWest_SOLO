from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from xiyou_solo.infra.session_store import DATA_DIR, read_json, write_json


ROOMS_PATH = DATA_DIR / "rooms.json"


@dataclass
class Room:
    group_id: str
    session_id: str
    host_user_id: str
    turn_order: List[str]
    current_turn_user_id: str
    status: str


def _default_rooms() -> Dict[str, Any]:
    return {"rooms": {}, "bindings": {}, "processed": {}, "rate_limit": {}}


def load_rooms() -> Dict[str, Any]:
    data = read_json(ROOMS_PATH, _default_rooms())
    data.setdefault("rooms", {})
    data.setdefault("bindings", {})
    data.setdefault("processed", {})
    data.setdefault("rate_limit", {})
    return data


def save_rooms(data: Dict[str, Any]) -> None:
    write_json(ROOMS_PATH, data)


def get_room(data: Dict[str, Any], group_id: str) -> Optional[Dict[str, Any]]:
    room = data.get("rooms", {}).get(group_id)
    return room if isinstance(room, dict) else None


def set_room(data: Dict[str, Any], group_id: str, room: Dict[str, Any]) -> None:
    data.setdefault("rooms", {})[group_id] = room


def remove_room(data: Dict[str, Any], group_id: str) -> None:
    data.setdefault("rooms", {}).pop(group_id, None)
    key_prefix = f"{group_id}:"
    bindings = data.setdefault("bindings", {})
    for key in [k for k in list(bindings.keys()) if k.startswith(key_prefix)]:
        bindings.pop(key, None)


def bind_player(data: Dict[str, Any], group_id: str, user_id: str, role_name: str) -> None:
    key = f"{group_id}:{user_id}"
    data.setdefault("bindings", {})[key] = {"role_name": role_name}


def get_binding(data: Dict[str, Any], group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    return data.setdefault("bindings", {}).get(f"{group_id}:{user_id}")


def list_group_bindings(data: Dict[str, Any], group_id: str) -> Dict[str, Dict[str, Any]]:
    prefix = f"{group_id}:"
    out: Dict[str, Dict[str, Any]] = {}
    for key, val in data.setdefault("bindings", {}).items():
        if key.startswith(prefix) and isinstance(val, dict):
            out[key[len(prefix) :]] = val
    return out


def ensure_room_shape(group_id: str, room: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(room)
    out["group_id"] = group_id
    out["session_id"] = str(out.get("session_id", "")).strip()
    out["host_user_id"] = str(out.get("host_user_id", "")).strip()
    turn_order = out.get("turn_order", [])
    out["turn_order"] = [str(x).strip() for x in turn_order if str(x).strip()] if isinstance(turn_order, list) else []
    current = str(out.get("current_turn_user_id", "")).strip()
    out["current_turn_user_id"] = current if current else (out["turn_order"][0] if out["turn_order"] else "")
    status = str(out.get("status", "waiting")).strip().lower()
    out["status"] = status if status in {"waiting", "running", "paused"} else "waiting"
    return out


def next_turn_user(room: Dict[str, Any]) -> str:
    order = room.get("turn_order", [])
    if not isinstance(order, list) or not order:
        room["current_turn_user_id"] = ""
        return ""
    current = str(room.get("current_turn_user_id", "")).strip()
    if current not in order:
        room["current_turn_user_id"] = str(order[0])
        return room["current_turn_user_id"]
    idx = order.index(current)
    nxt = str(order[(idx + 1) % len(order)])
    room["current_turn_user_id"] = nxt
    return nxt


def mark_processed(data: Dict[str, Any], message_id: str) -> None:
    data.setdefault("processed", {})[message_id] = True
    # Keep last 500 ids to avoid infinite growth.
    keys = list(data["processed"].keys())
    if len(keys) > 500:
        for k in keys[:-500]:
            data["processed"].pop(k, None)


def is_processed(data: Dict[str, Any], message_id: str) -> bool:
    return bool(data.setdefault("processed", {}).get(message_id))


def get_rate_limit_ts(data: Dict[str, Any], group_id: str, user_id: str) -> float:
    key = f"{group_id}:{user_id}"
    raw = data.setdefault("rate_limit", {}).get(key, 0.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def set_rate_limit_ts(data: Dict[str, Any], group_id: str, user_id: str, ts: float) -> None:
    key = f"{group_id}:{user_id}"
    data.setdefault("rate_limit", {})[key] = float(ts)
