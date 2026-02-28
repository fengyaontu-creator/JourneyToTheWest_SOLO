from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from xiyou_solo.core.state import GameState


BASE_DIR = Path(__file__).resolve().parents[1]
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
        max_attempts = 8
        session_id = ""
        for _ in range(max_attempts):
            session_id = make_session_id()
            try:
                self.session_dir(session_id).mkdir(parents=True, exist_ok=False)
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError(f"Failed to allocate unique session directory after {max_attempts} attempts")
        merged_meta: Dict[str, Any] = {"session_id": session_id, "created_at": utc_iso()}
        if player_id:
            merged_meta["player_id"] = player_id
        if meta:
            merged_meta.update(meta)
        merged_meta["session_id"] = session_id
        write_json(self._meta_path(session_id), merged_meta)
        return session_id

    def load_state(self, session_id: str) -> Dict[str, Any]:
        return read_json(self._state_path(session_id), {})

    def load_log(self, session_id: str) -> Dict[str, Any]:
        return read_json(self._log_path(session_id), {"session_id": session_id, "events": []})

    def load_meta(self, session_id: str) -> Dict[str, Any]:
        return read_json(self._meta_path(session_id), {"session_id": session_id})

    def save_state(self, session_id: str, state_obj: Dict[str, Any]) -> None:
        payload = dict(state_obj)
        payload["session_id"] = session_id
        write_json(self._state_path(session_id), payload)

    def save_log(self, session_id: str, log_obj: Dict[str, Any]) -> None:
        payload = dict(log_obj)
        payload["session_id"] = session_id
        payload.setdefault("events", [])
        write_json(self._log_path(session_id), payload)

    def save_meta(self, session_id: str, meta_obj: Dict[str, Any]) -> None:
        payload = dict(meta_obj)
        payload["session_id"] = session_id
        write_json(self._meta_path(session_id), payload)

    def list_sessions(self, player_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.ensure_dirs()
        sessions: List[Dict[str, Any]] = []
        for p in self.sessions_dir.iterdir():
            if not p.is_dir():
                continue
            sid = p.name
            if not self._state_path(sid).exists() or not self._log_path(sid).exists():
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
    session_store = store or SessionStore()
    candidates = [
        (DATA_DIR / "state.json", DATA_DIR / "log.json"),
        (SESSIONS_DIR / "state.json", SESSIONS_DIR / "log.json"),
    ]
    for legacy_state, legacy_log in candidates:
        if not legacy_state.exists() or not legacy_log.exists():
            continue
        old_state = read_json(legacy_state, {})
        old_log = read_json(legacy_log, {"events": []})
        meta: Dict[str, Any] = {"migrated_from": str(legacy_state.parent), "migration_at": utc_iso(), "source": "legacy_shared_files"}
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


class GameSessionStore:
    def __init__(self, session_store: Optional[SessionStore] = None):
        self._store = session_store or SessionStore()

    def create_session(self, player_id: Optional[str], meta: Optional[Dict[str, Any]] = None) -> str:
        return self._store.create_session(player_id=player_id, meta=meta)

    def list_sessions(self, player_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._store.list_sessions(player_id=player_id)

    def delete_session(self, session_id: str) -> None:
        self._store.delete_session(session_id)

    def load_game(self, session_id: str) -> Optional[Tuple[GameState, Dict[str, Any]]]:
        state = self._store.load_state(session_id)
        if not state:
            return None
        log_data = self._store.load_log(session_id)
        return GameState.from_dict(state), log_data

    def save_game(self, state: GameState, log_data: Dict[str, Any]) -> None:
        self._store.save_state(state.session_id, state.to_dict())
        self._store.save_log(state.session_id, log_data)

    def load_meta(self, session_id: str) -> Dict[str, Any]:
        return self._store.load_meta(session_id)

    def save_meta(self, session_id: str, meta_obj: Dict[str, Any]) -> None:
        self._store.save_meta(session_id, meta_obj)

    def get_active_session(self) -> Optional[str]:
        return get_active_session_id()

    def set_active_session(self, session_id: str) -> None:
        set_active_session_id(session_id)

    def clear_active_session(self) -> None:
        clear_active_session_id()

    def get_or_create_player_id(self) -> str:
        return get_or_create_cli_player_id()

    def migrate_legacy_shared(self, player_id: Optional[str]) -> Optional[str]:
        return migrate_legacy_shared_session(store=self._store, player_id=player_id)
