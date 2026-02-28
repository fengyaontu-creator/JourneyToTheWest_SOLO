from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
CLI_HOME_DIR = Path.home() / ".xiyou_solo"
CLI_PLAYER_ID_FILE = CLI_HOME_DIR / "player_id"
CLI_ACTIVE_SESSION_FILE = CLI_HOME_DIR / "active_session"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def make_session_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"sess_{stamp}_{uuid.uuid4().hex[:6]}"


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + f".tmp-{uuid.uuid4().hex}")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


class SessionStore:
    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir

    def ensure_dirs(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        return self.sessions_dir / session_id

    def _state_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "state.json"

    def _log_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "log.json"

    def _meta_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "meta.json"

    def create_session(self, player_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> str:
        self.ensure_dirs()
        session_id = make_session_id()
        if self.session_dir(session_id).exists():
            session_id = make_session_id()
        self.session_dir(session_id).mkdir(parents=True, exist_ok=True)
        merged_meta: Dict[str, Any] = {"session_id": session_id, "created_at": utc_iso()}
        if player_id:
            merged_meta["player_id"] = player_id
        if meta:
            merged_meta.update(meta)
        merged_meta["session_id"] = session_id
        if player_id and not merged_meta.get("player_id"):
            merged_meta["player_id"] = player_id
        write_json(self._meta_path(session_id), merged_meta)
        return session_id

    def load_state(self, session_id: str) -> Dict[str, Any]:
        return read_json(self._state_path(session_id), {})

    def load_log(self, session_id: str) -> Dict[str, Any]:
        return read_json(self._log_path(session_id), {"session_id": session_id, "events": []})

    def save_state(self, session_id: str, state_obj: Dict[str, Any]) -> None:
        payload = dict(state_obj)
        payload["session_id"] = session_id
        write_json(self._state_path(session_id), payload)

    def save_log(self, session_id: str, log_obj: Dict[str, Any]) -> None:
        payload = dict(log_obj)
        payload["session_id"] = session_id
        payload.setdefault("events", [])
        write_json(self._log_path(session_id), payload)

    def list_sessions(self, player_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.ensure_dirs()
        sessions: List[Dict[str, Any]] = []
        for p in self.sessions_dir.iterdir():
            if not p.is_dir():
                continue
            sid = p.name
            state_ok = self._state_path(sid).exists()
            log_ok = self._log_path(sid).exists()
            if not state_ok or not log_ok:
                continue
            meta = read_json(self._meta_path(sid), {})
            if player_id is not None and str(meta.get("player_id", "")).strip() != player_id:
                continue
            sessions.append({"session_id": sid, "meta": meta})
        sessions.sort(key=lambda row: (str(row.get("meta", {}).get("created_at", "")), row.get("session_id", "")), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> None:
        sdir = self.session_dir(session_id)
        if sdir.exists():
            shutil.rmtree(sdir)


def append_event(log_data: Dict[str, Any], event_type: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
    log_data.setdefault("events", []).append(
        {"type": event_type, "ts": utc_iso(), "content": content, "meta": meta or {}}
    )


def ensure_cli_home() -> None:
    CLI_HOME_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_cli_player_id() -> str:
    ensure_cli_home()
    if CLI_PLAYER_ID_FILE.exists():
        existing = CLI_PLAYER_ID_FILE.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    player_id = str(uuid.uuid4())
    CLI_PLAYER_ID_FILE.write_text(player_id, encoding="utf-8")
    return player_id


def get_active_session_id() -> Optional[str]:
    if not CLI_ACTIVE_SESSION_FILE.exists():
        return None
    sid = CLI_ACTIVE_SESSION_FILE.read_text(encoding="utf-8").strip()
    return sid or None


def set_active_session_id(session_id: str) -> None:
    ensure_cli_home()
    CLI_ACTIVE_SESSION_FILE.write_text(session_id, encoding="utf-8")


def clear_active_session_id() -> None:
    if CLI_ACTIVE_SESSION_FILE.exists():
        CLI_ACTIVE_SESSION_FILE.unlink()


def _backup_file(path: Path) -> None:
    target = path.with_suffix(path.suffix + ".bak")
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = path.with_suffix(path.suffix + f".bak.{stamp}")
    shutil.move(str(path), str(target))


def migrate_legacy_shared_session(store: Optional[SessionStore] = None, player_id: Optional[str] = None) -> Optional[str]:
    session_store = store or _DEFAULT_SESSION_STORE
    candidates = [
        (DATA_DIR / "state.json", DATA_DIR / "log.json"),
        (SESSIONS_DIR / "state.json", SESSIONS_DIR / "log.json"),
    ]
    for legacy_state, legacy_log in candidates:
        if not legacy_state.exists() or not legacy_log.exists():
            continue
        old_state = read_json(legacy_state, {})
        old_log = read_json(legacy_log, {"events": []})
        meta: Dict[str, Any] = {
            "migrated_from": str(legacy_state.parent),
            "migration_at": utc_iso(),
            "source": "legacy_shared_files",
        }
        if isinstance(old_state.get("language"), str):
            meta["language"] = old_state["language"]
        session_id = session_store.create_session(player_id=player_id, meta=meta)
        old_state["session_id"] = session_id
        old_log["session_id"] = session_id
        old_log.setdefault("events", [])
        session_store.save_state(session_id, old_state)
        session_store.save_log(session_id, old_log)
        _backup_file(legacy_state)
        _backup_file(legacy_log)
        return session_id
    return None


_DEFAULT_SESSION_STORE = SessionStore()


def ensure_dirs() -> None:
    _DEFAULT_SESSION_STORE.ensure_dirs()


def session_dir(session_id: str) -> Path:
    return _DEFAULT_SESSION_STORE.session_dir(session_id)


def session_files(session_id: str) -> Tuple[Path, Path]:
    sdir = session_dir(session_id)
    return sdir / "state.json", sdir / "log.json"


def save_session(state: Dict[str, Any], log_data: Dict[str, Any]) -> None:
    sid = str(state.get("session_id", "")).strip()
    if not sid:
        return
    _DEFAULT_SESSION_STORE.save_state(sid, state)
    _DEFAULT_SESSION_STORE.save_log(sid, log_data)


def load_session(session_id: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    state_path, log_path = session_files(session_id)
    if not state_path.exists() or not log_path.exists():
        return None
    state = _DEFAULT_SESSION_STORE.load_state(session_id)
    log_data = _DEFAULT_SESSION_STORE.load_log(session_id)
    return state, log_data


def list_sessions(player_id: Optional[str] = None) -> List[str]:
    return [row["session_id"] for row in _DEFAULT_SESSION_STORE.list_sessions(player_id=player_id)]


def delete_session(session_id: str) -> bool:
    if not session_dir(session_id).exists():
        return False
    _DEFAULT_SESSION_STORE.delete_session(session_id)
    if get_active_session_id() == session_id:
        clear_active_session_id()
    return True


# Backward-compatible aliases. CLI now uses ~/.xiyou_solo/active_session instead of data/current_session.txt.
def get_current_session_id() -> Optional[str]:
    return get_active_session_id()


def set_current_session_id(session_id: str) -> None:
    set_active_session_id(session_id)


def clear_current_session_id() -> None:
    clear_active_session_id()
