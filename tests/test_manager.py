import pytest

from life_reminder.manager import (
    add_custom,
    get_reminder,
    load_management,
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
