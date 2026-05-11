from datetime import date

from life_reminder.config import default_reminders_toml
from life_reminder.rules import (
    add_months,
    apply_haircut_weekend_policy,
    due_reminders,
    kst_datetime,
)

import tomllib


def config() -> dict[str, object]:
    return tomllib.loads(default_reminders_toml())


def test_haircut_first_booking_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-06-01", "08:45"), config())

    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.title == "미용실 예약"
    assert reminder.scheduled_at.isoformat() == "2026-06-01T08:45:00+09:00"
    assert "6월 7일 일요일 헤어컷 예정" in reminder.message
    assert "기준일: 6월 10일 수요일" in reminder.message
    assert "조정: 평일 -> 직전 일요일 6월 7일 일요일" in reminder.message
    assert "예약 알림: 6월 1일 월요일 08:45" in reminder.message


def test_haircut_weekend_candidate_is_not_moved() -> None:
    assert apply_haircut_weekend_policy(date(2026, 5, 10), "previous_sunday") == date(2026, 5, 10)
    assert apply_haircut_weekend_policy(date(2026, 6, 13), "previous_sunday") == date(2026, 6, 13)


def test_add_months_clamps_end_of_month() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_fingernails_weekly_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-05-17", "20:00"), config())

    assert any("손톱 자르기" in reminder.message for reminder in reminders)


def test_toenails_21_day_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-05-31", "20:00"), config())

    assert any("발톱 자르기" in reminder.message for reminder in reminders)


def test_trash_reminder_on_tuesday() -> None:
    reminders = due_reminders(kst_datetime("2026-05-12", "20:00"), config())

    assert any(reminder.title == "분리수거" for reminder in reminders)


def test_trash_reminder_not_on_monday() -> None:
    reminders = due_reminders(kst_datetime("2026-05-11", "20:00"), config())

    assert not any(reminder.title == "분리수거" for reminder in reminders)


def test_weekend_mac_and_cleaning_reminders() -> None:
    mac = due_reminders(kst_datetime("2026-05-16", "10:00"), config(), mac_status_text="배터리: 80%")
    cleaning = due_reminders(kst_datetime("2026-05-16", "10:30"), config())

    assert any(reminder.title == "맥북 상태점검" for reminder in mac)
    assert any(reminder.title == "주말 청소" for reminder in cleaning)
