from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PENDING = "pending"
COMPLETED = "completed"


class ConfirmationStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"telegram_update_offset": None, "items": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"telegram_update_offset": None, "items": {}}
        items = data.get("items", {})
        if not isinstance(items, dict):
            items = {}
        return {"telegram_update_offset": data.get("telegram_update_offset"), "items": items}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.path)

    def get(self, confirmation_id: str) -> dict[str, Any] | None:
        item = self.load()["items"].get(confirmation_id)
        return item if isinstance(item, dict) else None

    def upsert_pending(
        self,
        confirmation_id: str,
        reminder_id: str,
        title: str,
        message: str,
        prompt: str,
        scheduled_at: datetime,
        prompted_at: datetime,
        followup_days: int,
    ) -> dict[str, Any]:
        data = self.load()
        items = data["items"]
        current = items.get(confirmation_id, {})
        if not isinstance(current, dict):
            current = {}
        item = {
            **current,
            "confirmation_id": confirmation_id,
            "reminder_id": reminder_id,
            "status": current.get("status") or PENDING,
            "title": title,
            "message": message,
            "prompt": prompt,
            "scheduled_at": scheduled_at.isoformat(),
            "last_prompted_at": prompted_at.isoformat(),
            "completed_at": current.get("completed_at"),
            "last_answered_at": current.get("last_answered_at"),
            "last_answer": current.get("last_answer"),
            "followup_days": followup_days,
        }
        items[confirmation_id] = item
        self.save(data)
        return item

    def mark_answer(self, confirmation_id: str, answer: str, answered_at: datetime) -> dict[str, Any]:
        if answer not in {"yes", "no"}:
            raise ValueError("answer must be yes or no")
        data = self.load()
        items = data["items"]
        current = items.get(confirmation_id)
        if not isinstance(current, dict):
            raise KeyError(confirmation_id)
        current["last_answer"] = answer
        current["last_answered_at"] = answered_at.isoformat()
        if answer == "yes":
            current["status"] = COMPLETED
            current["completed_at"] = answered_at.isoformat()
        else:
            current["status"] = PENDING
            current["completed_at"] = None
        items[confirmation_id] = current
        self.save(data)
        return current

    def pending_items(self) -> list[dict[str, Any]]:
        items = self.load()["items"].values()
        return sorted(
            [item for item in items if isinstance(item, dict) and item.get("status") == PENDING],
            key=lambda item: str(item.get("scheduled_at", "")),
        )

    def update_offset(self, offset: int | None) -> None:
        data = self.load()
        data["telegram_update_offset"] = offset
        self.save(data)

    def update_offset_if_newer(self, offset: int) -> None:
        data = self.load()
        current = data.get("telegram_update_offset")
        if current is None or int(offset) > int(current):
            data["telegram_update_offset"] = offset
            self.save(data)

    def offset(self) -> int | None:
        offset = self.load().get("telegram_update_offset")
        return int(offset) if offset is not None else None


def confirmation_due(item: dict[str, Any], now: datetime, window_minutes: int = 4) -> bool:
    if item.get("status") != PENDING:
        return False
    last_prompted_at = parse_datetime(str(item.get("last_prompted_at", "")))
    followup_days = int(item.get("followup_days", 7))
    due_at = last_prompted_at + timedelta(days=followup_days)
    return abs(due_at - now) <= timedelta(minutes=window_minutes)


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
