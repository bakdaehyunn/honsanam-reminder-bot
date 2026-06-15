from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


RESPONSES = {"done", "later", "checked"}


class InteractionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"items": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"items": {}}
        items = data.get("items", {})
        if not isinstance(items, dict):
            items = {}
        return {"items": items}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.path)

    def upsert_sent(
        self,
        interaction_id: str,
        reminder_id: str,
        title: str,
        action: str,
        scheduled_at: datetime,
    ) -> dict[str, Any]:
        data = self.load()
        items = data["items"]
        current = items.get(interaction_id, {})
        if not isinstance(current, dict):
            current = {}
        item = {
            **current,
            "interaction_id": interaction_id,
            "reminder_id": reminder_id,
            "title": title,
            "action": action,
            "selected_response": current.get("selected_response"),
            "responded_at": current.get("responded_at"),
            "scheduled_at": scheduled_at.isoformat(),
            "telegram_update_id": current.get("telegram_update_id"),
        }
        items[interaction_id] = item
        self.save(data)
        return item

    def record_response(
        self,
        interaction_id: str,
        response: str,
        responded_at: datetime,
        telegram_update_id: int | None,
    ) -> dict[str, Any]:
        if response not in RESPONSES:
            raise ValueError("response must be done, later, or checked")
        data = self.load()
        items = data["items"]
        current = items.get(interaction_id)
        if not isinstance(current, dict):
            raise KeyError(interaction_id)
        current["selected_response"] = response
        current["responded_at"] = responded_at.isoformat()
        current["telegram_update_id"] = telegram_update_id
        items[interaction_id] = current
        self.save(data)
        return current

    def list_items(self) -> list[dict[str, Any]]:
        return sorted(
            [item for item in self.load()["items"].values() if isinstance(item, dict)],
            key=lambda item: (str(item.get("scheduled_at", "")), str(item.get("interaction_id", ""))),
        )
