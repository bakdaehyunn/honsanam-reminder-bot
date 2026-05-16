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
        mac_status_default_note(mac_status_text),
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
        "주말 청소 루틴 진행하기",
        fixed_weekly_default_note("weekend-cleaning"),
        tz,
        pattern,
    )
    if cleaning:
        items.append(cleaning)
    bedding = interval_reminder(
        now,
        config.get("bedding", {}),
        "bedding-wash",
        "이불 빨래",
        "이불 빨래하기",
        bedding_default_note,
        tz,
        pattern,
    )
    if bedding:
        items.append(bedding)
    bathroom = interval_reminder(
        now,
        config.get("bathroom", {}),
        "bathroom-cleaning",
        "화장실 청소",
        "화장실 청소하기",
        bathroom_default_note,
        tz,
        pattern,
    )
    if bathroom:
        items.append(bathroom)
    nose_hair = interval_reminder(
        now,
        config.get("nose_hair", {}),
        "nose-hair",
        "코털 정리",
        "코털 정리하기",
        nose_hair_default_note,
        tz,
        pattern,
    )
    if nose_hair:
        items.append(nose_hair)
    earwax = interval_reminder(
        now,
        config.get("earwax", {}),
        "earwax",
        "귀지 정리",
        "귀 주변 정리하기",
        earwax_default_note,
        tz,
        pattern,
    )
    if earwax:
        items.append(earwax)
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
                    str(settings.get("note") or haircut_note()),
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
                    str(settings.get("fingernails_note") or fingernails_default_note()),
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
                    str(settings.get("toenails_note") or toenails_default_note()),
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
            str(settings.get("note") or trash_default_note()),
            pattern,
        ),
    )


def trash_default_note() -> str:
    return "\n".join(
        [
            "오늘 23:00쯤 수거 예정입니다.",
            "종량제 봉투와 음식물 봉투 여유분도 확인해 주세요.",
            "재활용품은 비우고 헹구면 뒤처리가 편합니다.",
        ]
    )


def fingernails_default_note() -> str:
    return "\n".join(
        [
            "손톱 끝만 깔끔하게 정리하기",
            "손 볼 때 생각보다 티 납니다.",
        ]
    )


def toenails_default_note() -> str:
    return "\n".join(
        [
            "길어지기 전에 미리 정리하기",
            "양말 신을 때 거슬리기 전에 정리해 주세요.",
        ]
    )


def weekly_reminder(
    now: datetime,
    settings: dict[str, Any],
    reminder_id: str,
    title: str,
    default_action: str,
    default_note: str,
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
            str(settings.get("action") or default_action),
            str(settings.get("note") or default_note),
            pattern,
        ),
    )


def interval_reminder(
    now: datetime,
    settings: dict[str, Any],
    reminder_id: str,
    title: str,
    action: str,
    default_note_func: Any,
    tz: object,
    pattern: MessagePattern,
) -> Reminder | None:
    if not settings.get("enabled", True):
        return None
    base = parse_date(str(settings.get("base_date", "2026-05-10")))
    days = int(settings.get("days", 14))
    if days < 1:
        return None
    days_since = (now.date() - base).days
    if days_since < 0 or days_since % days != 0:
        return None
    scheduled = datetime.combine(now.date(), parse_time(str(settings.get("notify_time", "11:00"))), tzinfo=tz)
    title = str(settings.get("title") or title)
    return Reminder(
        reminder_id=f"{reminder_id}-{now.date().isoformat()}",
        scheduled_at=scheduled,
        title=title,
        message=card(
            title,
            f"{days}일 주기, {format_date_ko(now.date())} {scheduled:%H:%M}",
            str(settings.get("action") or action),
            str(settings.get("note") or default_note_func()),
            pattern,
        ),
    )


def fixed_weekly_default_note(reminder_id: str) -> str:
    if reminder_id == "weekend-cleaning":
        return "\n".join(
            [
                "바닥, 책상, 설거지, 쓰레기부터 정리하기",
                "집이 정리되면 주말이 덜 밀립니다.",
            ]
        )
    return ""


def mac_status_default_note(status_text: str) -> str:
    lines = []
    if status_text:
        lines.append(status_text)
    else:
        lines.append("상태 수집 결과가 없습니다.")
    lines.extend(
        [
            "배터리, 저장공간, 업데이트 상태 확인하기",
            "오래 켜져 있으면 재부팅 한 번 해 주세요.",
        ]
    )
    return "\n".join(lines)


def bedding_default_note() -> str:
    return "\n".join(
        [
            "이불 커버와 베개 커버도 같이 확인하기",
            "잠자리가 산뜻하면 잠도 편합니다.",
        ]
    )


def bathroom_default_note() -> str:
    return "\n".join(
        [
            "변기, 세면대, 배수구부터 정리하기",
            "화장실은 미루면 바로 티 납니다.",
        ]
    )


def nose_hair_default_note() -> str:
    return "\n".join(
        [
            "거울 보고 삐져나온 것만 정리하기",
            "말할 때 은근히 먼저 보입니다.",
        ]
    )


def earwax_default_note() -> str:
    return "\n".join(
        [
            "면봉으로 깊게 파지 말고 겉만 정리하기",
            "이어폰 쓸 때 생각보다 신경 쓰입니다.",
        ]
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


def haircut_note() -> str:
    return "\n".join(
        [
            "이번 주 가능한 시간 먼저 확인하기",
            "머리만 정리해도 인상이 꽤 달라집니다.",
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
