from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
CURRENT_SESSION_FILE = DATA_DIR / "current_session.txt"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def make_session_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"sess_{stamp}"


def ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def session_files(session_id: str) -> Tuple[Path, Path]:
    sdir = session_dir(session_id)
    return sdir / "state.json", sdir / "log.json"


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_event(log_data: Dict[str, Any], event_type: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
    log_data.setdefault("events", []).append(
        {"type": event_type, "ts": utc_iso(), "content": content, "meta": meta or {}}
    )


def save_session(state: Dict[str, Any], log_data: Dict[str, Any]) -> None:
    sid = str(state.get("session_id", "")).strip()
    if not sid:
        return
    state_path, log_path = session_files(sid)
    write_json(state_path, state)
    write_json(log_path, log_data)
    set_current_session_id(sid)


def load_session(session_id: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    state_path, log_path = session_files(session_id)
    if not state_path.exists() or not log_path.exists():
        return None
    state = read_json(state_path, {})
    log_data = read_json(log_path, {"session_id": session_id, "events": []})
    return state, log_data


def list_sessions() -> List[str]:
    ensure_dirs()
    ids: List[str] = []
    for p in SESSIONS_DIR.iterdir():
        if p.is_dir() and (p / "state.json").exists() and (p / "log.json").exists():
            ids.append(p.name)
    ids.sort(reverse=True)
    return ids


def delete_session(session_id: str) -> bool:
    sdir = session_dir(session_id)
    if not sdir.exists():
        return False
    shutil.rmtree(sdir)
    if get_current_session_id() == session_id:
        clear_current_session_id()
    return True


def get_current_session_id() -> Optional[str]:
    if not CURRENT_SESSION_FILE.exists():
        return None
    sid = CURRENT_SESSION_FILE.read_text(encoding="utf-8").strip()
    return sid or None


def set_current_session_id(session_id: str) -> None:
    CURRENT_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_SESSION_FILE.write_text(session_id, encoding="utf-8")


def clear_current_session_id() -> None:
    if CURRENT_SESSION_FILE.exists():
        CURRENT_SESSION_FILE.unlink()

