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
            if "base_date" in values:
                config["haircut"]["base_date"] = values["base_date"]
        elif reminder_id in {"fingernails", "toenails"}:
            section = config.setdefault("nails", {})
            if "enabled" in values:
                section[f"{reminder_id}_enabled"] = bool(values["enabled"])
            if "time" in values:
                section["notify_time"] = values["time"]
            if "base_date" in values:
                section["base_date"] = values["base_date"]
            if "days" in values:
                section[f"{reminder_id}_days"] = values["days"]
            for key in ("title", "action", "note"):
                if key in values:
                    section[f"{reminder_id}_{key}"] = values[key]
        elif reminder_id == "trash":
            apply_section(config.setdefault("trash", {}), values)
        elif reminder_id == "mac-status":
            apply_section(config.setdefault("mac_status", {}), values)
        elif reminder_id == "weekend-cleaning":
            apply_section(config.setdefault("cleaning", {}), values)
        elif reminder_id == "bedding-wash":
            apply_section(config.setdefault("bedding", {}), values)
            for key in ("base_date", "days"):
                if key in values:
                    config["bedding"][key] = values[key]
        elif reminder_id == "bathroom-cleaning":
            apply_section(config.setdefault("bathroom", {}), values)
            for key in ("base_date", "days"):
                if key in values:
                    config["bathroom"][key] = values[key]


def apply_section(section: dict[str, Any], values: dict[str, Any]) -> None:
    if "enabled" in values:
        section["enabled"] = bool(values["enabled"])
    if "time" in values:
        section["notify_time"] = values["time"]
    if "weekday" in values:
        section["weekday"] = values["weekday"]
    for key in ("title", "action", "note"):
        if key in values:
            section[key] = values[key]


def list_reminders(management: dict[str, Any], effective_config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    fixed = management.get("fixed", {})
    rows = []
    for reminder_id in sorted(FIXED_IDS):
        values = fixed.get(reminder_id, {}) if isinstance(fixed, dict) else {}
        effective = fixed_effective_values(reminder_id, effective_config) if effective_config is not None else {}
        rows.append({"id": reminder_id, "type": "fixed", **effective, **values})
    rows.extend({"type": "custom", **record} for record in management.get("custom", []))
    return rows


def get_reminder(management: dict[str, Any], reminder_id: str, effective_config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if reminder_id in FIXED_IDS:
        fixed = management.get("fixed", {})
        values = fixed.get(reminder_id, {}) if isinstance(fixed, dict) else {}
        effective = fixed_effective_values(reminder_id, effective_config) if effective_config is not None else {}
        return {"id": reminder_id, "type": "fixed", **effective, **values}
    for record in management.get("custom", []):
        if isinstance(record, dict) and record.get("id") == reminder_id:
            return {"type": "custom", **record}
    return None


def fixed_effective_values(reminder_id: str, config: dict[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return {}
    if reminder_id == "haircut":
        section = config.get("haircut", {})
        return section_values(section, "미용실 예약", "오늘 미용실 예약하기", "이번 주 가능한 시간 먼저 확인하기\n머리만 정리해도 인상이 꽤 달라집니다.")
    if reminder_id == "trash":
        section = config.get("trash", {})
        return section_values(section, "분리수거", "오늘 분리수거 내놓기", "오늘 23:00쯤 수거 예정입니다.\n종량제 봉투와 음식물 봉투 여유분도 확인해 주세요.\n재활용품은 비우고 헹구면 뒤처리가 편합니다.", extra_keys=("weekdays",))
    if reminder_id == "mac-status":
        section = config.get("mac_status", {})
        return section_values(section, "맥북 상태점검", "맥북 상태 확인", "배터리, 저장공간, 업데이트 상태 확인하기\n오래 켜져 있으면 재부팅 한 번 해 주세요.", extra_keys=("weekday",))
    if reminder_id == "weekend-cleaning":
        section = config.get("cleaning", {})
        return section_values(section, "주말 청소", "주말 청소 루틴 진행하기", "바닥, 책상, 설거지, 쓰레기부터 정리하기\n집이 정리되면 주말이 덜 밀립니다.", extra_keys=("weekday",))
    if reminder_id == "bedding-wash":
        section = config.get("bedding", {})
        return section_values(section, "이불 빨래", "이불 빨래하기", "이불 커버와 베개 커버도 같이 확인하기\n잠자리가 산뜻하면 잠도 편합니다.", extra_keys=("base_date", "days"))
    if reminder_id == "bathroom-cleaning":
        section = config.get("bathroom", {})
        return section_values(section, "화장실 청소", "화장실 청소하기", "변기, 세면대, 배수구부터 정리하기\n화장실은 미루면 바로 티 납니다.", extra_keys=("base_date", "days"))
    if reminder_id in {"fingernails", "toenails"}:
        section = config.get("nails", {})
        if not isinstance(section, dict):
            return {}
        title = "손톱 관리" if reminder_id == "fingernails" else "발톱 관리"
        action = "손톱 자르기" if reminder_id == "fingernails" else "발톱 자르기"
        note = (
            "손톱 끝만 깔끔하게 정리하기\n손 볼 때 생각보다 티 납니다."
            if reminder_id == "fingernails"
            else "길어지기 전에 미리 정리하기\n양말 신을 때 거슬리기 전에 정리해 주세요."
        )
        prefix = reminder_id
        return {
            "enabled": bool(section.get("enabled", True)) and bool(section.get(f"{prefix}_enabled", True)),
            "title": section.get(f"{prefix}_title", title),
            "time": section.get("notify_time"),
            "base_date": section.get("base_date"),
            "days": section.get(f"{prefix}_days"),
            "action": section.get(f"{prefix}_action", action),
            "note": section.get(f"{prefix}_note", note),
        }
    return {}


def section_values(
    section: object,
    default_title: str,
    default_action: str,
    default_note: str,
    extra_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    if not isinstance(section, dict):
        return {}
    values: dict[str, Any] = {
        "enabled": bool(section.get("enabled", True)),
        "title": section.get("title", default_title),
        "time": section.get("notify_time"),
        "action": section.get("action", default_action),
        "note": section.get("note", default_note),
    }
    for key in extra_keys:
        if key in section:
            values[key] = section[key]
    return values


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
