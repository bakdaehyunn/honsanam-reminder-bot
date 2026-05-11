from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MessagePattern:
    prefix: str = "생활알림"
    schedule_label: str = "언제"
    action_label: str = "해야 할 일"
    note_label: str = "확인할 점"


def load_pattern(path: Path) -> MessagePattern:
    default = MessagePattern()
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return default
    return MessagePattern(
        prefix=str(data.get("prefix") or default.prefix),
        schedule_label=str(data.get("schedule_label") or default.schedule_label),
        action_label=str(data.get("action_label") or default.action_label),
        note_label=str(data.get("note_label") or default.note_label),
    )


def save_pattern(path: Path, pattern: MessagePattern) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(asdict(pattern), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def update_pattern(path: Path, **values: str | None) -> MessagePattern:
    current = load_pattern(path)
    updated = MessagePattern(
        prefix=values.get("prefix") or current.prefix,
        schedule_label=values.get("schedule_label") or current.schedule_label,
        action_label=values.get("action_label") or current.action_label,
        note_label=values.get("note_label") or current.note_label,
    )
    save_pattern(path, updated)
    return updated
