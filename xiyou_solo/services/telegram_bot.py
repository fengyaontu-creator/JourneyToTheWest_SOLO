from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from xiyou_solo.services.tg_handler import handle_chat_text


MAX_REPLY_LEN = 3500


def _api_base(token: str) -> str:
    return f"https://api.telegram.org/bot{token}"


def _http_get_json(url: str, timeout: int = 40) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _http_post_json(url: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def send_message(token: str, chat_id: int, text: str) -> None:
    safe_text = (text or "").strip()
    if not safe_text:
        return
    if len(safe_text) > MAX_REPLY_LEN:
        safe_text = safe_text[:MAX_REPLY_LEN] + "\n...[truncated]"
    url = f"{_api_base(token)}/sendMessage"
    payload = {"chat_id": chat_id, "text": safe_text}
    try:
        _http_post_json(url, payload)
    except Exception as exc:
        print(f"[warn] sendMessage failed: {exc}")


def _extract_messages(updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in updates:
        if not isinstance(item, dict):
            continue
        msg = item.get("message")
        if not isinstance(msg, dict):
            continue
        chat = msg.get("chat", {})
        if not isinstance(chat, dict):
            continue
        chat_id = chat.get("id")
        text = msg.get("text", "")
        upd_id = item.get("update_id")
        if chat_id is None or upd_id is None or not isinstance(text, str):
            continue
        out.append({"update_id": int(upd_id), "chat_id": int(chat_id), "text": text})
    return out


def run_polling() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN. Please set environment variable first.")
        return

    offset = 0
    print("Telegram bot polling started.")
    while True:
        try:
            params = urllib.parse.urlencode({"timeout": 30, "offset": offset})
            url = f"{_api_base(token)}/getUpdates?{params}"
            obj = _http_get_json(url, timeout=40)
            if not obj.get("ok", False):
                print(f"[warn] getUpdates not ok: {obj}")
                time.sleep(2)
                continue
            updates = obj.get("result", [])
            if not isinstance(updates, list):
                time.sleep(1)
                continue

            for row in _extract_messages(updates):
                offset = max(offset, int(row["update_id"]) + 1)
                try:
                    reply = handle_chat_text(int(row["chat_id"]), str(row["text"]))
                except Exception as exc:
                    reply = f"Internal error: {exc}"
                send_message(token, int(row["chat_id"]), reply)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[warn] polling error: {exc}")
            time.sleep(2)
        except KeyboardInterrupt:
            print("Telegram bot stopped.")
            break
        except Exception as exc:
            print(f"[warn] unexpected error: {exc}")
            time.sleep(2)


if __name__ == "__main__":
    run_polling()
