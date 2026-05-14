from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class TelegramChatCandidate:
    chat_id: str
    title: str
    chat_type: str


class TelegramClient:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    def get_me(self) -> dict[str, object]:
        return self._api("getMe", {})

    def get_updates(self) -> dict[str, object]:
        return self._api("getUpdates", {"limit": "100"})

    def send_message(self, text: str) -> None:
        self._api(
            "sendMessage",
            {
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
            method="POST",
        )

    def _api(self, method_name: str, params: dict[str, str], method: str = "GET") -> dict[str, object]:
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is empty")
        url = f"https://api.telegram.org/bot{self.token}/{method_name}"
        data = None
        if method == "GET":
            if params:
                url = f"{url}?{urlencode(params)}"
        else:
            data = urlencode(params).encode("utf-8")
        req = Request(url, data=data, method=method)
        with urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise RuntimeError(f"Telegram API failed: {payload}")
        return payload


def discover_chat_candidates(payload: dict[str, object]) -> list[TelegramChatCandidate]:
    result = payload.get("result", [])
    if not isinstance(result, list):
        return []

    candidates: list[TelegramChatCandidate] = []
    seen: set[str] = set()
    for update in result:
        if not isinstance(update, dict):
            continue
        for key in ("message", "edited_message", "channel_post", "edited_channel_post", "my_chat_member", "chat_member"):
            event = update.get(key)
            if not isinstance(event, dict):
                continue
            chat = event.get("chat")
            if not isinstance(chat, dict):
                continue
            raw_chat_id = chat.get("id")
            if raw_chat_id is None:
                continue
            chat_id = str(raw_chat_id)
            if chat_id in seen:
                continue
            seen.add(chat_id)
            chat_type = str(chat.get("type", ""))
            title = str(chat.get("title") or chat.get("username") or chat.get("first_name") or chat_type or chat_id)
            candidates.append(TelegramChatCandidate(chat_id=chat_id, title=title, chat_type=chat_type))
    return candidates
