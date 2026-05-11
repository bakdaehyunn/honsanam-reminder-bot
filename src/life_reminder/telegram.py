from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TelegramClient:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    def get_me(self) -> dict[str, object]:
        return self._api("getMe", {})

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
