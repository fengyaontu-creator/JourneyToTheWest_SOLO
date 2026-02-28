from __future__ import annotations

import hashlib
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from xiyou_solo.services.game_service import TurnExecutor, handle_message


WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "").strip()
HOST = os.getenv("WECHAT_ADAPTER_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("WECHAT_ADAPTER_PORT", "8090"))

_TURN_EXECUTOR: Optional[TurnExecutor] = None


def set_turn_executor(executor: Optional[TurnExecutor]) -> None:
    global _TURN_EXECUTOR
    _TURN_EXECUTOR = executor


def verify_signature(token: str, timestamp: str, nonce: str, signature: str) -> bool:
    """
    WeChat-style signature check:
    sha1(sort([token, timestamp, nonce]).join(""))
    """
    if not token:
        return False
    raw = "".join(sorted([token, timestamp, nonce]))
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return digest == signature


def parse_event(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Generic normalized event format expected by game_service.
    """
    return {
        "group_id": str(payload.get("group_id", "")).strip(),
        "user_id": str(payload.get("user_id", "")).strip(),
        "message_id": str(payload.get("message_id", "")).strip(),
        "text": str(payload.get("text", "")).strip(),
    }


class WeChatCallbackHandler(BaseHTTPRequestHandler):
    server_version = "xiyou-wechat-adapter/0.1"

    def _send_json(self, status: int, obj: Dict[str, Any]) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        signature = (qs.get("signature") or [""])[0]
        timestamp = (qs.get("timestamp") or [""])[0]
        nonce = (qs.get("nonce") or [""])[0]
        echostr = (qs.get("echostr") or [""])[0]

        if verify_signature(WECHAT_TOKEN, timestamp, nonce, signature):
            body = echostr.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "invalid signature"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/wechat/callback", "/callback"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return

        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid content-length"})
            return
        body = self.rfile.read(max(0, length))
        try:
            payload = json.loads(body.decode("utf-8") if body else "{}")
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid json"})
            return

        event = parse_event(payload if isinstance(payload, dict) else {})
        if not event["group_id"] or not event["user_id"]:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing group_id/user_id"})
            return

        replies = handle_message(
            group_id=event["group_id"],
            user_id=event["user_id"],
            text=event["text"],
            message_id=event["message_id"],
            turn_executor=_TURN_EXECUTOR,
        )
        self._send_json(HTTPStatus.OK, {"ok": True, "replies": replies})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Quiet default logging; keep adapter output clean.
        return


def run_server(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), WeChatCallbackHandler)
    print(f"WeChat adapter listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
