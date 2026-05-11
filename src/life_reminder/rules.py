from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from life_reminder.messages import card
from life_reminder.patterns import MessagePattern


WEEKDAYS = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}
WEEKDAY_KO = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


@dataclass(frozen=True)
class Reminder:
    reminder_id: str
    scheduled_at: datetime
    title: str
    message: str

    @property
    def sent_key(self) -> str:
        return f"{self.reminder_id}:{self.scheduled_at.isoformat()}"


def due_reminders(
    now: datetime,
    config: dict[str, Any],
    window_minutes: int = 4,
    mac_status_text: str = "",
    pattern: MessagePattern | None = None,
) -> list[Reminder]:
    now = now.replace(second=0, microsecond=0)
    reminders = scheduled_reminders_near(now, config, mac_status_text=mac_status_text, pattern=pattern)
    return [
        reminder
        for reminder in reminders
        if abs(reminder.scheduled_at - now) <= timedelta(minutes=window_minutes)
    ]


def scheduled_reminders_near(
    now: datetime,
    config: dict[str, Any],
    mac_status_text: str = "",
    pattern: MessagePattern | None = None,
) -> list[Reminder]:
    tz = now.tzinfo
    items: list[Reminder] = []
    pattern = pattern or MessagePattern()
    items.extend(haircut_reminders(now, config.get("haircut", {}), tz, pattern))
    items.extend(nail_reminders(now, config.get("nails", {}), tz, pattern))
    trash = trash_reminder(now, config.get("trash", {}), tz, pattern)
    if trash:
        items.append(trash)
    mac = weekly_reminder(
        now,
        config.get("mac_status", {}),
        "mac-status",
        "맥북 상태점검",
        "맥북 상태 확인",
        mac_status_text or "상태 수집 결과가 없습니다.",
        tz,
        pattern,
    )
    if mac:
        items.append(mac)
    cleaning = weekly_reminder(
        now,
        config.get("cleaning", {}),
        "weekend-cleaning",
        "주말 청소",
        "주말 청소 루틴",
        "청소기, 책상 정리, 쓰레기 정리 확인",
        tz,
        pattern,
    )
    if cleaning:
        items.append(cleaning)
    items.extend(custom_reminders(now, config.get("custom", []), tz, pattern))
    return items


def haircut_reminders(now: datetime, settings: dict[str, Any], tz: object, pattern: MessagePattern) -> list[Reminder]:
    if not settings.get("enabled", True):
        return []
    base = parse_date(str(settings.get("base_date", "2026-05-10")))
    interval_months = int(settings.get("interval_months", 1))
    notify = parse_time(str(settings.get("notify_time", "08:45")))
    reminders: list[Reminder] = []
    for step in range(interval_months, interval_months * 61, interval_months):
        candidate = add_months(base, step)
        haircut_day = apply_haircut_weekend_policy(candidate, str(settings.get("weekend_policy", "previous_sunday")))
        notify_day = haircut_day - timedelta(days=haircut_day.weekday())
        if abs((notify_day - now.date()).days) > 1:
            continue
        scheduled = datetime.combine(notify_day, notify, tzinfo=tz)
        reminders.append(
            Reminder(
                reminder_id=f"haircut-booking-{haircut_day.isoformat()}",
                scheduled_at=scheduled,
                title=str(settings.get("title") or "미용실 예약"),
                message=card(
                    str(settings.get("title") or "미용실 예약"),
                    f"{format_date_ko(haircut_day)} 헤어컷 예정",
                    str(settings.get("action") or "오늘 미용실 예약하기"),
                    str(settings.get("note") or haircut_note(candidate, haircut_day, notify_day)),
                    pattern,
                ),
            )
        )
    return reminders


def nail_reminders(now: datetime, settings: dict[str, Any], tz: object, pattern: MessagePattern) -> list[Reminder]:
    if not settings.get("enabled", True):
        return []
    base = parse_date(str(settings.get("base_date", "2026-05-10")))
    notify = parse_time(str(settings.get("notify_time", "20:00")))
    scheduled = datetime.combine(now.date(), notify, tzinfo=tz)
    reminders: list[Reminder] = []
    days_since = (now.date() - base).days
    fingernails_days = int(settings.get("fingernails_days", 7))
    toenails_days = int(settings.get("toenails_days", 21))
    if settings.get("fingernails_enabled", True) and days_since >= 0 and days_since % fingernails_days == 0:
        title = str(settings.get("fingernails_title") or "손톱 관리")
        reminders.append(
            Reminder(
                reminder_id="fingernails",
                scheduled_at=scheduled,
                title=title,
                message=card(
                    title,
                    f"손톱 {fingernails_days}일 주기",
                    str(settings.get("fingernails_action") or "손톱 자르기"),
                    str(settings.get("fingernails_note") or ""),
                    pattern,
                ),
            )
        )
    if settings.get("toenails_enabled", True) and days_since >= 0 and days_since % toenails_days == 0:
        title = str(settings.get("toenails_title") or "발톱 관리")
        reminders.append(
            Reminder(
                reminder_id="toenails",
                scheduled_at=scheduled,
                title=title,
                message=card(
                    title,
                    f"발톱 {toenails_days}일 주기",
                    str(settings.get("toenails_action") or "발톱 자르기"),
                    str(settings.get("toenails_note") or ""),
                    pattern,
                ),
            )
        )
    return reminders


def trash_reminder(now: datetime, settings: dict[str, Any], tz: object, pattern: MessagePattern) -> Reminder | None:
    if not settings.get("enabled", True):
        return None
    weekdays = {WEEKDAYS[item] for item in settings.get("weekdays", ["tue", "thu", "sun"])}
    if now.weekday() not in weekdays:
        return None
    scheduled = datetime.combine(now.date(), parse_time(str(settings.get("notify_time", "20:00"))), tzinfo=tz)
    return Reminder(
        reminder_id=f"trash-{now.date().isoformat()}",
        scheduled_at=scheduled,
        title=str(settings.get("title") or "분리수거"),
        message=card(
            str(settings.get("title") or "분리수거"),
            f"{format_date_ko(now.date())} {scheduled:%H:%M}",
            str(settings.get("action") or "오늘 분리수거 내놓기"),
            str(settings.get("note") or "화/목/일 11시 수거 기준"),
            pattern,
        ),
    )


def weekly_reminder(
    now: datetime,
    settings: dict[str, Any],
    reminder_id: str,
    title: str,
    schedule: str,
    action: str,
    tz: object,
    pattern: MessagePattern,
) -> Reminder | None:
    if not settings.get("enabled", True):
        return None
    weekday = WEEKDAYS[str(settings.get("weekday", "sat"))]
    if now.weekday() != weekday:
        return None
    scheduled = datetime.combine(now.date(), parse_time(str(settings.get("notify_time", "10:00"))), tzinfo=tz)
    title = str(settings.get("title") or title)
    return Reminder(
        reminder_id=f"{reminder_id}-{now.date().isoformat()}",
        scheduled_at=scheduled,
        title=title,
        message=card(
            title,
            f"{format_date_ko(now.date())} {scheduled:%H:%M}",
            str(settings.get("action") or action),
            str(settings.get("note") or ""),
            pattern,
        ),
    )


def custom_reminders(now: datetime, records: object, tz: object, pattern: MessagePattern) -> list[Reminder]:
    if not isinstance(records, list):
        return []
    reminders: list[Reminder] = []
    for record in records:
        if not isinstance(record, dict) or not record.get("enabled", True):
            continue
        kind = str(record.get("kind", ""))
        scheduled = custom_scheduled_at(now, record, kind, tz)
        if scheduled is None:
            continue
        title = str(record.get("title") or record.get("id"))
        reminders.append(
            Reminder(
                reminder_id=str(record["id"]),
                scheduled_at=scheduled,
                title=title,
                message=card(
                    title,
                    custom_schedule_text(now, record, kind, scheduled),
                    str(record.get("action") or title),
                    str(record.get("note") or ""),
                    pattern,
                ),
            )
        )
    return reminders


def custom_scheduled_at(now: datetime, record: dict[str, Any], kind: str, tz: object) -> datetime | None:
    notify = parse_time(str(record.get("time", "00:00")))
    if kind == "one-off":
        target = parse_date(str(record.get("date")))
        if target != now.date():
            return None
        return datetime.combine(target, notify, tzinfo=tz)
    if kind == "weekly":
        weekday = WEEKDAYS[str(record.get("weekday"))]
        if now.weekday() != weekday:
            return None
        return datetime.combine(now.date(), notify, tzinfo=tz)
    if kind == "interval":
        base = parse_date(str(record.get("base_date")))
        days = int(record.get("days", 1))
        elapsed = (now.date() - base).days
        if elapsed < 0 or elapsed % days != 0:
            return None
        return datetime.combine(now.date(), notify, tzinfo=tz)
    return None


def custom_schedule_text(now: datetime, record: dict[str, Any], kind: str, scheduled: datetime) -> str:
    if kind == "one-off":
        return f"{format_date_ko(scheduled.date())} {scheduled:%H:%M}"
    if kind == "weekly":
        return f"매주 {WEEKDAY_KO[scheduled.weekday()]} {scheduled:%H:%M}"
    if kind == "interval":
        return f"{record.get('days')}일마다 {scheduled:%H:%M}"
    return f"{format_date_ko(now.date())} {scheduled:%H:%M}"


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def apply_haircut_weekend_policy(value: date, policy: str) -> date:
    if policy != "previous_sunday":
        raise ValueError(f"unsupported haircut weekend_policy: {policy}")
    if value.weekday() <= 4:
        return value - timedelta(days=value.weekday() + 1)
    return value


def haircut_note(candidate: date, haircut_day: date, notify_day: date) -> str:
    if candidate == haircut_day:
        return f"기준일: {format_date_ko(candidate)}\n조정: 주말이라 그대로 진행"
    return "\n".join(
        [
            f"기준일: {format_date_ko(candidate)}",
            f"조정: 평일 -> 직전 일요일 {format_date_ko(haircut_day)}",
            f"예약 알림: {format_date_ko(notify_day)} 08:45",
        ]
    )


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def format_date_ko(value: date) -> str:
    return f"{value.month}월 {value.day}일 {WEEKDAY_KO[value.weekday()]}"


def kst_datetime(date_text: str, time_text: str) -> datetime:
    return datetime.combine(parse_date(date_text), parse_time(time_text), tzinfo=ZoneInfo("Asia/Seoul"))
