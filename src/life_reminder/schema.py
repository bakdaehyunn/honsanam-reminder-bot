from __future__ import annotations

import re
from datetime import date


WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
CUSTOM_KINDS = {"one-off", "weekly", "interval"}
FIXED_IDS = {
    "bathroom-cleaning",
    "bedding-wash",
    "haircut",
    "fingernails",
    "toenails",
    "nose-hair",
    "earwax",
    "trash",
    "mac-status",
    "weekend-cleaning",
}
FIXED_UPDATE_FIELDS = {
    "haircut": {"enabled", "title", "action", "note", "time", "base_date"},
    "fingernails": {"enabled", "title", "action", "note", "time", "base_date", "days"},
    "toenails": {"enabled", "title", "action", "note", "time", "base_date", "days"},
    "nose-hair": {"enabled", "title", "action", "note", "time", "base_date", "days"},
    "earwax": {"enabled", "title", "action", "note", "time", "base_date", "days"},
    "trash": {"enabled", "title", "action", "note", "time"},
    "mac-status": {"enabled", "title", "action", "note", "time", "weekday"},
    "weekend-cleaning": {"enabled", "title", "action", "note", "time", "weekday"},
    "bedding-wash": {"enabled", "title", "action", "note", "time", "base_date", "days"},
    "bathroom-cleaning": {"enabled", "title", "action", "note", "time", "base_date", "days"},
}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ValidationError(ValueError):
    pass


def validate_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise ValidationError("id must match ^[a-z][a-z0-9-]{1,63}$")
    return value


def validate_time(value: str) -> str:
    if not TIME_PATTERN.fullmatch(value):
        raise ValidationError("time must be HH:MM")
    return value


def validate_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("date must be YYYY-MM-DD") from exc
    return value


def validate_weekday(value: str) -> str:
    if value not in WEEKDAYS:
        raise ValidationError("weekday must be one of mon,tue,wed,thu,fri,sat,sun")
    return value


def validate_days(value: int) -> int:
    if value < 1:
        raise ValidationError("days must be >= 1")
    return value


def validate_custom(record: dict[str, object]) -> None:
    reminder_id = validate_id(str(record.get("id", "")))
    if reminder_id in FIXED_IDS:
        raise ValidationError(f"id conflicts with fixed reminder: {reminder_id}")
    title = str(record.get("title", "")).strip()
    action = str(record.get("action", "")).strip()
    kind = str(record.get("kind", ""))
    if not title:
        raise ValidationError("title is required")
    if not action:
        raise ValidationError("action is required")
    if kind not in CUSTOM_KINDS:
        raise ValidationError("kind must be one-off, weekly, or interval")
    validate_time(str(record.get("time", "")))
    if kind == "one-off":
        validate_date(str(record.get("date", "")))
    elif kind == "weekly":
        validate_weekday(str(record.get("weekday", "")))
    elif kind == "interval":
        validate_date(str(record.get("base_date", "")))
        validate_days(int(record.get("days", 0)))


def validate_fixed_update(reminder_id: str, values: dict[str, object]) -> None:
    if reminder_id not in FIXED_IDS:
        raise ValidationError(f"unknown fixed reminder: {reminder_id}")
    allowed = FIXED_UPDATE_FIELDS[reminder_id]
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValidationError(f"{reminder_id} does not support field(s): {', '.join(unknown)}")
    if "time" in values:
        validate_time(str(values["time"]))
    if "base_date" in values:
        validate_date(str(values["base_date"]))
    if "days" in values:
        validate_days(int(values["days"]))
    if "weekday" in values:
        validate_weekday(str(values["weekday"]))
    for key in ("title", "action", "note"):
        if key in values and not str(values[key]).strip():
            raise ValidationError(f"{key} must not be empty")
