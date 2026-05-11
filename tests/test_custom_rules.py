from life_reminder.patterns import MessagePattern
from life_reminder.rules import due_reminders, kst_datetime


def test_custom_one_off_reminder() -> None:
    reminders = due_reminders(
        kst_datetime("2026-05-20", "09:00"),
        {
            "custom": [
                {
                    "id": "passport",
                    "title": "여권 확인",
                    "kind": "one-off",
                    "date": "2026-05-20",
                    "time": "09:00",
                    "action": "여권 만료일 확인",
                    "note": "",
                    "enabled": True,
                }
            ]
        },
    )

    assert len(reminders) == 1
    assert reminders[0].reminder_id == "passport"
    assert "여권 만료일 확인" in reminders[0].message


def test_custom_weekly_reminder() -> None:
    reminders = due_reminders(
        kst_datetime("2026-05-16", "09:30"),
        {
            "custom": [
                {
                    "id": "plants",
                    "title": "화분 물주기",
                    "kind": "weekly",
                    "weekday": "sat",
                    "time": "09:30",
                    "action": "화분 물주기",
                    "note": "",
                    "enabled": True,
                }
            ]
        },
    )

    assert len(reminders) == 1
    assert "매주 토요일 09:30" in reminders[0].message


def test_custom_interval_reminder() -> None:
    reminders = due_reminders(
        kst_datetime("2026-05-24", "21:00"),
        {
            "custom": [
                {
                    "id": "filter",
                    "title": "필터 청소",
                    "kind": "interval",
                    "base_date": "2026-05-10",
                    "days": 14,
                    "time": "21:00",
                    "action": "공기청정기 필터 청소",
                    "note": "",
                    "enabled": True,
                }
            ]
        },
    )

    assert len(reminders) == 1
    assert "14일마다 21:00" in reminders[0].message


def test_message_pattern_changes_labels_and_omits_empty_note() -> None:
    reminders = due_reminders(
        kst_datetime("2026-05-20", "09:00"),
        {
            "custom": [
                {
                    "id": "passport",
                    "title": "여권 확인",
                    "kind": "one-off",
                    "date": "2026-05-20",
                    "time": "09:00",
                    "action": "여권 만료일 확인",
                    "note": "",
                    "enabled": True,
                }
            ]
        },
        pattern=MessagePattern(prefix="알림", schedule_label="시점", action_label="처리", note_label="참고"),
    )

    message = reminders[0].message
    assert message.startswith("알림 | 여권 확인")
    assert "시점\n" in message
    assert "처리\n" in message
    assert "참고" not in message
