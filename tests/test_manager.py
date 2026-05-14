import pytest

from life_reminder.manager import (
    add_custom,
    get_reminder,
    load_management,
    merge_config,
    remove_reminder,
    set_enabled,
    update_reminder,
)
from life_reminder.schema import ValidationError


def test_add_update_remove_custom_reminder(tmp_path) -> None:
    path = tmp_path / "reminders.json"

    add_custom(
        path,
        {
            "id": "water-plants",
            "title": "화분 물주기",
            "kind": "weekly",
            "weekday": "sat",
            "time": "09:00",
            "action": "화분 물주기",
            "note": "",
            "enabled": True,
        },
    )
    update_reminder(path, "water-plants", {"time": "09:30", "note": "거실 먼저 확인"})
    set_enabled(path, "water-plants", False)

    row = get_reminder(load_management(path), "water-plants")
    assert row is not None
    assert row["time"] == "09:30"
    assert row["note"] == "거실 먼저 확인"
    assert row["enabled"] is False

    remove_reminder(path, "water-plants")
    assert get_reminder(load_management(path), "water-plants") is None


def test_fixed_reminder_can_be_disabled_but_not_removed(tmp_path) -> None:
    path = tmp_path / "reminders.json"

    set_enabled(path, "trash", False)

    row = get_reminder(load_management(path), "trash")
    assert row is not None
    assert row["enabled"] is False
    with pytest.raises(ValidationError):
        remove_reminder(path, "trash")


def test_bedding_fixed_reminder_schedule_can_be_updated(tmp_path) -> None:
    path = tmp_path / "reminders.json"

    update_reminder(path, "bedding-wash", {"time": "12:00", "base_date": "2026-05-11", "days": 21})

    config = merge_config({"bedding": {"enabled": True, "base_date": "2026-05-10", "days": 14, "notify_time": "11:00"}}, load_management(path))
    assert config["bedding"]["notify_time"] == "12:00"
    assert config["bedding"]["base_date"] == "2026-05-11"
    assert config["bedding"]["days"] == 21


def test_bathroom_fixed_reminder_schedule_can_be_updated(tmp_path) -> None:
    path = tmp_path / "reminders.json"

    update_reminder(path, "bathroom-cleaning", {"time": "09:30", "base_date": "2026-05-12", "days": 14})

    config = merge_config({"bathroom": {"enabled": True, "base_date": "2026-05-11", "days": 14, "notify_time": "10:30"}}, load_management(path))
    assert config["bathroom"]["notify_time"] == "09:30"
    assert config["bathroom"]["base_date"] == "2026-05-12"
    assert config["bathroom"]["days"] == 14


@pytest.mark.parametrize(
    "record",
    [
        {"id": "Bad ID", "title": "x", "kind": "weekly", "weekday": "sat", "time": "09:00", "action": "x"},
        {"id": "bad-weekday", "title": "x", "kind": "weekly", "weekday": "noday", "time": "09:00", "action": "x"},
        {"id": "bad-time", "title": "x", "kind": "weekly", "weekday": "sat", "time": "25:00", "action": "x"},
        {"id": "missing-date", "title": "x", "kind": "one-off", "time": "09:00", "action": "x"},
    ],
)
def test_invalid_custom_reminders_are_rejected(tmp_path, record) -> None:
    with pytest.raises((ValidationError, TypeError)):
        add_custom(tmp_path / "reminders.json", record)
