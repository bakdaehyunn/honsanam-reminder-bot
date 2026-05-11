from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from life_reminder.schema import FIXED_IDS, ValidationError, validate_custom, validate_fixed_update


def empty_management() -> dict[str, Any]:
    return {"fixed": {}, "custom": []}


def load_management(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_management()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError("management file must be a JSON object")
    fixed = data.get("fixed", {})
    custom = data.get("custom", [])
    if not isinstance(fixed, dict) or not isinstance(custom, list):
        raise ValidationError("management file must contain fixed object and custom list")
    return {"fixed": fixed, "custom": custom}


def save_management(path: Path, data: dict[str, Any]) -> None:
    validate_management(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def validate_management(data: dict[str, Any]) -> None:
    fixed = data.get("fixed", {})
    custom = data.get("custom", [])
    if not isinstance(fixed, dict) or not isinstance(custom, list):
        raise ValidationError("fixed must be object and custom must be list")
    for reminder_id, values in fixed.items():
        if not isinstance(values, dict):
            raise ValidationError(f"fixed {reminder_id} must be an object")
        validate_fixed_update(str(reminder_id), values)
    seen: set[str] = set()
    for record in custom:
        if not isinstance(record, dict):
            raise ValidationError("custom reminder must be an object")
        validate_custom(record)
        reminder_id = str(record["id"])
        if reminder_id in seen:
            raise ValidationError(f"duplicate custom id: {reminder_id}")
        seen.add(reminder_id)


def merge_config(base: dict[str, Any], management: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base)
    fixed = management.get("fixed", {})
    if isinstance(fixed, dict):
        apply_fixed_overrides(config, fixed)
    config["custom"] = list(management.get("custom", []))
    return config


def apply_fixed_overrides(config: dict[str, Any], fixed: dict[str, Any]) -> None:
    for reminder_id, values in fixed.items():
        if not isinstance(values, dict):
            continue
        if reminder_id == "haircut":
            apply_section(config.setdefault("haircut", {}), values)
        elif reminder_id in {"fingernails", "toenails"}:
            section = config.setdefault("nails", {})
            if "enabled" in values:
                section[f"{reminder_id}_enabled"] = bool(values["enabled"])
            if "time" in values:
                section["notify_time"] = values["time"]
            for key in ("title", "action", "note"):
                if key in values:
                    section[f"{reminder_id}_{key}"] = values[key]
        elif reminder_id == "trash":
            apply_section(config.setdefault("trash", {}), values)
        elif reminder_id == "mac-status":
            apply_section(config.setdefault("mac_status", {}), values)
        elif reminder_id == "weekend-cleaning":
            apply_section(config.setdefault("cleaning", {}), values)


def apply_section(section: dict[str, Any], values: dict[str, Any]) -> None:
    if "enabled" in values:
        section["enabled"] = bool(values["enabled"])
    if "time" in values:
        section["notify_time"] = values["time"]
    for key in ("title", "action", "note"):
        if key in values:
            section[key] = values[key]


def list_reminders(management: dict[str, Any]) -> list[dict[str, Any]]:
    fixed = management.get("fixed", {})
    rows = [{"id": reminder_id, "type": "fixed", **(fixed.get(reminder_id, {}) if isinstance(fixed, dict) else {})} for reminder_id in sorted(FIXED_IDS)]
    rows.extend({"type": "custom", **record} for record in management.get("custom", []))
    return rows


def get_reminder(management: dict[str, Any], reminder_id: str) -> dict[str, Any] | None:
    if reminder_id in FIXED_IDS:
        fixed = management.get("fixed", {})
        values = fixed.get(reminder_id, {}) if isinstance(fixed, dict) else {}
        return {"id": reminder_id, "type": "fixed", **values}
    for record in management.get("custom", []):
        if isinstance(record, dict) and record.get("id") == reminder_id:
            return {"type": "custom", **record}
    return None


def set_enabled(path: Path, reminder_id: str, enabled: bool) -> None:
    data = load_management(path)
    if reminder_id in FIXED_IDS:
        data.setdefault("fixed", {}).setdefault(reminder_id, {})["enabled"] = enabled
    else:
        record = find_custom(data, reminder_id)
        record["enabled"] = enabled
    save_management(path, data)


def add_custom(path: Path, record: dict[str, Any]) -> None:
    data = load_management(path)
    validate_custom(record)
    if get_reminder(data, str(record["id"])) is not None:
        raise ValidationError(f"reminder already exists: {record['id']}")
    data.setdefault("custom", []).append(record)
    save_management(path, data)


def update_reminder(path: Path, reminder_id: str, values: dict[str, Any]) -> None:
    data = load_management(path)
    clean = {key: value for key, value in values.items() if value is not None}
    if reminder_id in FIXED_IDS:
        validate_fixed_update(reminder_id, clean)
        data.setdefault("fixed", {}).setdefault(reminder_id, {}).update(clean)
    else:
        record = find_custom(data, reminder_id)
        record.update(clean)
        validate_custom(record)
    save_management(path, data)


def remove_reminder(path: Path, reminder_id: str) -> None:
    if reminder_id in FIXED_IDS:
        raise ValidationError("fixed reminders cannot be removed")
    data = load_management(path)
    custom = data.get("custom", [])
    next_custom = [record for record in custom if not isinstance(record, dict) or record.get("id") != reminder_id]
    if len(next_custom) == len(custom):
        raise ValidationError(f"unknown custom reminder: {reminder_id}")
    data["custom"] = next_custom
    save_management(path, data)


def find_custom(data: dict[str, Any], reminder_id: str) -> dict[str, Any]:
    for record in data.get("custom", []):
        if isinstance(record, dict) and record.get("id") == reminder_id:
            return record
    raise ValidationError(f"unknown reminder: {reminder_id}")
