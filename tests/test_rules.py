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
    assert "관리 포인트" in reminder.message
    assert "이번 주 가능한 시간 먼저 확인하기" in reminder.message
    assert "머리만 정리해도 인상이 꽤 달라집니다." in reminder.message


def test_haircut_weekend_candidate_is_not_moved() -> None:
    assert apply_haircut_weekend_policy(date(2026, 5, 10), "previous_sunday") == date(2026, 5, 10)
    assert apply_haircut_weekend_policy(date(2026, 6, 13), "previous_sunday") == date(2026, 6, 13)


def test_add_months_clamps_end_of_month() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_fingernails_weekly_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-05-20", "21:00"), config())

    reminder = next(reminder for reminder in reminders if reminder.title == "손톱 관리")
    assert "손톱 자르기" in reminder.message
    assert "손톱 끝만 깔끔하게 정리하기" in reminder.message
    assert "손 볼 때 생각보다 티 납니다." in reminder.message


def test_toenails_21_day_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-06-03", "21:00"), config())

    reminder = next(reminder for reminder in reminders if reminder.title == "발톱 관리")
    assert "발톱 자르기" in reminder.message
    assert "길어지기 전에 미리 정리하기" in reminder.message
    assert "양말 신을 때 거슬리기 전에 정리해 주세요." in reminder.message


def test_trash_reminder_on_tuesday() -> None:
    reminders = due_reminders(kst_datetime("2026-05-12", "20:00"), config())

    assert any(reminder.title == "분리수거" for reminder in reminders)
    trash = next(reminder for reminder in reminders if reminder.title == "분리수거")
    assert "오늘 23:00쯤 수거 예정입니다." in trash.message
    assert "종량제 봉투와 음식물 봉투 여유분도 확인해 주세요." in trash.message
    assert "재활용품은 비우고 헹구면 뒤처리가 편합니다." in trash.message


def test_trash_reminder_not_on_monday() -> None:
    reminders = due_reminders(kst_datetime("2026-05-11", "20:00"), config())

    assert not any(reminder.title == "분리수거" for reminder in reminders)


def test_weekend_mac_and_cleaning_reminders() -> None:
    mac = due_reminders(kst_datetime("2026-05-16", "10:00"), config(), mac_status_text="배터리: 80%")
    cleaning = due_reminders(kst_datetime("2026-05-16", "14:00"), config())

    assert any(reminder.title == "맥북 상태점검" for reminder in mac)
    mac_reminder = next(reminder for reminder in mac if reminder.title == "맥북 상태점검")
    assert "맥북 상태 확인" in mac_reminder.message
    assert "배터리: 80%" in mac_reminder.message
    assert "배터리, 저장공간, 업데이트 상태 확인하기" in mac_reminder.message
    assert "오래 켜져 있으면 재부팅 한 번 해 주세요." in mac_reminder.message
    assert any(reminder.title == "주말 청소" for reminder in cleaning)
    cleaning_reminder = next(reminder for reminder in cleaning if reminder.title == "주말 청소")
    assert "바닥, 책상, 설거지, 쓰레기부터 정리하기" in cleaning_reminder.message
    assert "집이 정리되면 주말이 덜 밀립니다." in cleaning_reminder.message


def test_bedding_wash_interval_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-06-07", "14:00"), config())

    reminder = next(reminder for reminder in reminders if reminder.title == "이불 빨래")
    assert reminder.scheduled_at.isoformat() == "2026-06-07T14:00:00+09:00"
    assert "14일 주기" in reminder.message
    assert "이불 커버와 베개 커버도 같이 확인하기" in reminder.message
    assert "잠자리가 산뜻하면 잠도 편합니다." in reminder.message


def test_bedding_wash_not_due_between_intervals() -> None:
    reminders = due_reminders(kst_datetime("2026-05-31", "14:00"), config())

    assert not any(reminder.title == "이불 빨래" for reminder in reminders)


def test_bathroom_cleaning_interval_reminder() -> None:
    reminders = due_reminders(kst_datetime("2026-05-31", "10:30"), config())

    reminder = next(reminder for reminder in reminders if reminder.title == "화장실 청소")
    assert reminder.scheduled_at.isoformat() == "2026-05-31T10:30:00+09:00"
    assert "14일 주기" in reminder.message
    assert "변기, 세면대, 배수구부터 정리하기" in reminder.message
    assert "화장실은 미루면 바로 티 납니다." in reminder.message
