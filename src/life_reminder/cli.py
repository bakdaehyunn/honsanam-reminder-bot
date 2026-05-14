from __future__ import annotations

import argparse
import getpass
import json
import subprocess
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from life_reminder.config import (
    DEFAULT_ENV_FILE,
    ROOT,
    Settings,
    get_settings,
    load_env,
    load_reminders,
    write_default_files,
)
from life_reminder.mac_status import collect_status
from life_reminder.manager import (
    add_custom,
    get_reminder,
    list_reminders,
    load_management,
    merge_config,
    remove_reminder,
    set_enabled,
    update_reminder,
    validate_management,
)
from life_reminder.messages import card
from life_reminder.patterns import MessagePattern, load_pattern, update_pattern
from life_reminder.rules import WEEKDAYS, Reminder, due_reminders, kst_datetime, parse_time, scheduled_reminders_near
from life_reminder.schema import ValidationError
from life_reminder.state import SentStore, file_lock
from life_reminder.telegram import TelegramClient, discover_chat_candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="honsanam-reminder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create local config files")

    p_setup = sub.add_parser("setup", help="Configure local env and setup checks")
    p_setup.add_argument("--dry-run", action="store_true")
    p_setup.add_argument("--non-interactive", action="store_true")
    p_setup.add_argument("--telegram-bot-token")
    p_setup.add_argument("--telegram-chat-id")
    p_setup.add_argument("--timezone")
    p_setup.add_argument("--install-launchd", action="store_true")

    sub.add_parser("doctor", help="Check config and Telegram connectivity")

    p_discover_chat = sub.add_parser("discover-chat", help="Find Telegram chat id from recent bot updates")
    p_discover_chat.add_argument("--plain", action="store_true")
    p_discover_chat.add_argument("--json", action="store_true")

    p_preview = sub.add_parser("preview", help="Preview reminders due at a specific KST time")
    p_preview.add_argument("--date", required=True)
    p_preview.add_argument("--time", required=True)

    p_run = sub.add_parser("run-once", help="Send reminders due now")
    p_run.add_argument("--dry-run", action="store_true")

    sub.add_parser("send-test", help="Send one test message to the reminder chat")
    p_next = sub.add_parser("next", help="Show upcoming reminders")
    p_next.add_argument("--days", type=int, default=14)
    p_next.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="List reminders")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="Show one reminder")
    p_show.add_argument("id")
    p_show.add_argument("--json", action="store_true")

    p_enable = sub.add_parser("enable", help="Enable a reminder")
    p_enable.add_argument("id")

    p_disable = sub.add_parser("disable", help="Disable a reminder")
    p_disable.add_argument("id")

    p_remove = sub.add_parser("remove", help="Remove a custom reminder")
    p_remove.add_argument("id")

    p_add = sub.add_parser("add", help="Add a reminder")
    add_sub = p_add.add_subparsers(dest="add_kind", required=True)
    p_add_custom = add_sub.add_parser("custom", help="Add a custom reminder")
    p_add_custom.add_argument("--id", required=True)
    p_add_custom.add_argument("--title", required=True)
    p_add_custom.add_argument("--kind", required=True, choices=["one-off", "weekly", "interval"])
    p_add_custom.add_argument("--time", required=True)
    p_add_custom.add_argument("--action", required=True)
    p_add_custom.add_argument("--note", default="")
    p_add_custom.add_argument("--date")
    p_add_custom.add_argument("--weekday")
    p_add_custom.add_argument("--base-date")
    p_add_custom.add_argument("--days", type=int)

    p_update = sub.add_parser("update", help="Update a reminder")
    p_update.add_argument("id")
    p_update.add_argument("--title")
    p_update.add_argument("--time")
    p_update.add_argument("--action")
    p_update.add_argument("--note")
    p_update.add_argument("--date")
    p_update.add_argument("--weekday")
    p_update.add_argument("--base-date")
    p_update.add_argument("--days", type=int)

    p_pattern = sub.add_parser("pattern", help="Manage message pattern")
    pattern_sub = p_pattern.add_subparsers(dest="pattern_cmd", required=True)
    pattern_sub.add_parser("show")
    p_pattern_set = pattern_sub.add_parser("set")
    p_pattern_set.add_argument("--prefix")
    p_pattern_set.add_argument("--schedule-label")
    p_pattern_set.add_argument("--action-label")
    p_pattern_set.add_argument("--note-label")

    sub.add_parser("validate", help="Validate reminder management config")

    args = parser.parse_args(argv)
    if args.cmd == "init":
        return init_cmd()

    settings = get_settings()
    if args.cmd == "setup":
        return setup_cmd(
            settings,
            dry_run=args.dry_run,
            non_interactive=args.non_interactive,
            telegram_bot_token=args.telegram_bot_token,
            telegram_chat_id=args.telegram_chat_id,
            timezone=args.timezone,
            install_launchd=args.install_launchd,
        )
    if args.cmd == "doctor":
        return doctor_cmd(settings)
    if args.cmd == "discover-chat":
        return discover_chat_cmd(settings, plain=args.plain, json_output=args.json)
    if args.cmd == "preview":
        return preview_cmd(settings, args.date, args.time)
    if args.cmd == "run-once":
        return run_once_cmd(settings, dry_run=args.dry_run)
    if args.cmd == "send-test":
        return send_test_cmd(settings)
    if args.cmd == "next":
        return next_cmd(settings, days=args.days, json_output=args.json)
    if args.cmd == "list":
        return list_cmd(settings, json_output=args.json)
    if args.cmd == "show":
        return show_cmd(settings, args.id, json_output=args.json)
    if args.cmd == "enable":
        return enabled_cmd(settings, args.id, True)
    if args.cmd == "disable":
        return enabled_cmd(settings, args.id, False)
    if args.cmd == "remove":
        return remove_cmd(settings, args.id)
    if args.cmd == "add":
        return add_cmd(settings, args)
    if args.cmd == "update":
        return update_cmd(settings, args)
    if args.cmd == "pattern":
        return pattern_cmd(settings, args)
    if args.cmd == "validate":
        return validate_cmd(settings)
    return 2


def init_cmd() -> int:
    try:
        created = write_default_files(ROOT)
    except Exception as exc:
        print(f"[FAIL] init failed: {exc}")
        return 1
    if created:
        for path in created:
            print(f"created {path}")
    else:
        print("nothing to create")
    return 0


def setup_cmd(
    settings: Settings,
    dry_run: bool,
    non_interactive: bool,
    telegram_bot_token: str | None,
    telegram_chat_id: str | None,
    timezone: str | None,
    install_launchd: bool,
) -> int:
    print("==> Creating default project files")
    if dry_run:
        print(f"[dry-run] ensure default files under {settings.root}")
    else:
        try:
            created = write_default_files(settings.root)
        except Exception as exc:
            print(f"[FAIL] setup failed: {exc}")
            return 1
        if created:
            for path in created:
                print(f"created {path}")
        else:
            print("nothing to create")

    env = load_env(settings.env_file)
    token = choose_setup_value(
        label="Telegram bot token",
        current=env.get("TELEGRAM_BOT_TOKEN", ""),
        provided=telegram_bot_token,
        secret=True,
        non_interactive=non_interactive,
    )
    tz = choose_setup_value(
        label="Timezone",
        current=env.get("LIFE_REMINDER_TIMEZONE", "Asia/Seoul") or "Asia/Seoul",
        provided=timezone,
        secret=False,
        non_interactive=non_interactive,
    )
    chat_id = telegram_chat_id or env.get("TELEGRAM_REMINDER_CHAT_ID", "")

    if not token:
        print("[FAIL] Telegram bot token is required")
        return 1
    if not tz:
        print("[FAIL] timezone is required")
        return 1

    if not chat_id:
        chat_id = discover_chat_for_setup(token, dry_run=dry_run, non_interactive=non_interactive)
    if not chat_id and not non_interactive:
        chat_id = prompt_setup_value("Telegram reminder chat id", "", secret=True)
    if not chat_id:
        print("[FAIL] Telegram reminder chat id is required")
        return 1

    print("==> Writing configuration")
    if dry_run:
        print(f"[dry-run] write {settings.env_file}")
    else:
        write_setup_env(settings.env_file, token, chat_id, tz)

    configured = get_settings(settings.env_file)
    print("==> Checking configuration")
    if dry_run:
        print("[dry-run] honsanam-reminder doctor")
    else:
        doctor_cmd(configured)

    print("==> Upcoming reminders")
    if dry_run:
        print("[dry-run] honsanam-reminder next --days 14")
    else:
        next_cmd(configured, days=14, json_output=False)

    if sys.platform == "darwin":
        should_install_launchd = install_launchd
        if not non_interactive and not install_launchd:
            should_install_launchd = ask_yes_no("Install macOS automatic launchd schedule?", default=False)
        if should_install_launchd:
            launchd_status = install_launch_agent(settings.root, dry_run=dry_run)
            if launchd_status != 0:
                return launchd_status
        else:
            print("skipped launchd install")

    print("setup complete")
    print("Run `honsanam-reminder send-test` when you want to verify Telegram delivery.")
    return 0


def choose_setup_value(
    label: str,
    current: str,
    provided: str | None,
    secret: bool,
    non_interactive: bool,
) -> str:
    if provided is not None:
        return provided.strip()
    if non_interactive:
        return current.strip()
    return prompt_setup_value(label, current, secret=secret)


def prompt_setup_value(label: str, current: str, secret: bool) -> str:
    if current:
        prompt = f"{label} [configured]: " if secret else f"{label} [{current}]: "
    else:
        prompt = f"{label}: "
    if secret:
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    return current if not value else value.strip()


def write_setup_env(env_file: Path, token: str, chat_id: str, timezone: str) -> None:
    env_file.write_text(
        f"TELEGRAM_BOT_TOKEN={token}\n"
        f"TELEGRAM_REMINDER_CHAT_ID={chat_id}\n"
        f"LIFE_REMINDER_TIMEZONE={timezone}\n",
        encoding="utf-8",
    )


def discover_chat_for_setup(token: str, dry_run: bool, non_interactive: bool) -> str:
    print("Telegram chat id can be found automatically after the bot receives one message.")
    if dry_run:
        print("[dry-run] honsanam-reminder discover-chat --plain")
        return ""
    if not non_interactive and not ask_yes_no("Try chat id auto discovery?", default=True):
        return ""
    if not non_interactive:
        input("Send any message to your Telegram bot, then press Enter here.")
    try:
        payload = TelegramClient(token, "").get_updates()
        candidates = discover_chat_candidates(payload)
    except Exception as exc:
        print(f"could not find chat id automatically: {exc}")
        return ""
    if not candidates:
        print("could not find chat id automatically")
        return ""
    print("found Telegram reminder chat id")
    return candidates[-1].chat_id


def ask_yes_no(question: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def install_launch_agent(root: Path, dry_run: bool) -> int:
    script = root / "scripts/install_launch_agent.sh"
    if dry_run:
        print(f"[dry-run] {script}")
        return 0
    try:
        subprocess.run([str(script)], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[FAIL] launchd install failed: {exc}")
        return 1
    return 0


def doctor_cmd(settings: Settings) -> int:
    lines, ok = diagnose(settings, check_telegram=True)
    print("\n".join(lines))
    return 0 if ok else 1


def discover_chat_cmd(settings: Settings, plain: bool, json_output: bool) -> int:
    if not settings.telegram_bot_token:
        print("[FAIL] TELEGRAM_BOT_TOKEN is empty")
        return 1
    try:
        payload = TelegramClient(settings.telegram_bot_token, settings.telegram_reminder_chat_id).get_updates()
        candidates = discover_chat_candidates(payload)
    except Exception as exc:
        print(f"[FAIL] Telegram getUpdates failed: {exc}")
        return 1
    if not candidates:
        print("[FAIL] no Telegram chat found. Send a message to the bot, then run this command again.")
        return 1
    if json_output:
        print(json.dumps([candidate.__dict__ for candidate in candidates], ensure_ascii=False, indent=2))
        return 0
    latest = candidates[-1]
    if plain:
        print(latest.chat_id)
        return 0
    print(f"chat_id: {latest.chat_id}")
    if latest.title:
        print(f"title: {latest.title}")
    if latest.chat_type:
        print(f"type: {latest.chat_type}")
    return 0


def diagnose(settings: Settings, check_telegram: bool) -> tuple[list[str], bool]:
    lines: list[str] = []
    ok = True
    if settings.env_file.exists():
        lines.append(f"[OK] env_file={settings.env_file}")
    else:
        lines.append(f"[FAIL] env_file missing: {settings.env_file}")
        ok = False
    if settings.telegram_bot_token:
        lines.append("[OK] TELEGRAM_BOT_TOKEN is set")
    else:
        lines.append("[FAIL] TELEGRAM_BOT_TOKEN is empty")
        ok = False
    if settings.telegram_reminder_chat_id:
        lines.append("[OK] TELEGRAM_REMINDER_CHAT_ID is set")
    else:
        lines.append("[FAIL] TELEGRAM_REMINDER_CHAT_ID is empty")
        ok = False
    if settings.reminders_file.exists():
        lines.append(f"[OK] reminders_file={settings.reminders_file}")
        try:
            load_reminders(settings.reminders_file)
            lines.append("[OK] reminders.toml is readable")
        except Exception as exc:
            lines.append(f"[FAIL] reminders.toml is invalid: {exc}")
            ok = False
    else:
        lines.append(f"[FAIL] reminders_file missing: {settings.reminders_file}")
        ok = False
    try:
        settings.state_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.state_dir / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        lines.append(f"[OK] state_dir writable: {settings.state_dir}")
    except Exception as exc:
        lines.append(f"[FAIL] state_dir not writable: {exc}")
        ok = False
    try:
        settings.config_dir.mkdir(parents=True, exist_ok=True)
        validate_management(load_management(settings.management_file))
        lines.append(f"[OK] management config is valid: {settings.management_file}")
    except Exception as exc:
        lines.append(f"[FAIL] management config is invalid: {exc}")
        ok = False
    try:
        load_pattern(settings.pattern_file)
        lines.append(f"[OK] message pattern is valid: {settings.pattern_file}")
    except Exception as exc:
        lines.append(f"[FAIL] message pattern is invalid: {exc}")
        ok = False
    if check_telegram and settings.telegram_bot_token:
        try:
            payload = TelegramClient(settings.telegram_bot_token, settings.telegram_reminder_chat_id).get_me()
            result = payload.get("result", {}) if isinstance(payload, dict) else {}
            username = result.get("username", "") if isinstance(result, dict) else ""
            lines.append(f"[OK] Telegram getMe succeeded: @{username}")
        except Exception as exc:
            lines.append(f"[FAIL] Telegram getMe failed: {exc}")
            ok = False
    return lines, ok


def preview_cmd(settings: Settings, date_text: str, time_text: str) -> int:
    config = load_effective_config(settings)
    pattern = load_pattern(settings.pattern_file)
    now = kst_datetime(date_text, time_text)
    reminders = due_reminders(now, config, mac_status_text=mac_status_if_needed(now, config), pattern=pattern)
    if not reminders:
        print("No reminders due.")
        return 0
    print_reminders(reminders)
    return 0


def run_once_cmd(settings: Settings, dry_run: bool) -> int:
    config = load_effective_config(settings)
    pattern = load_pattern(settings.pattern_file)
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz).replace(second=0, microsecond=0)
    reminders = due_reminders(now, config, mac_status_text=mac_status_if_needed(now, config), pattern=pattern)
    store = SentStore(settings.state_dir / "sent.json")
    pending = [reminder for reminder in reminders if not store.has(reminder.sent_key)]

    if dry_run:
        if not pending:
            print("No reminders due.")
        else:
            print_reminders(pending)
        return 0

    with file_lock(settings.state_dir / "run.lock") as acquired:
        if not acquired:
            print("Another run is already active.")
            return 0
        client = TelegramClient(settings.telegram_bot_token, settings.telegram_reminder_chat_id)
        for reminder in pending:
            client.send_message(reminder.message)
            store.add(reminder.sent_key)
            print(f"sent {reminder.sent_key}")
    if not pending:
        print("No reminders due.")
    return 0


def send_test_cmd(settings: Settings) -> int:
    pattern = load_pattern(settings.pattern_file)
    message = card(
        "알림 연결 점검",
        "지금",
        "생활알림방까지 Telegram 전송이 정상인지 확인하기",
        "이 메시지가 보이면 자동 알림이 같은 방으로 도착합니다.",
        pattern,
    )
    TelegramClient(settings.telegram_bot_token, settings.telegram_reminder_chat_id).send_message(message)
    print("sent test message")
    return 0


def print_reminders(reminders: list[Reminder]) -> None:
    for index, reminder in enumerate(reminders):
        if index:
            print("\n---\n")
        print(f"# {reminder.title} @ {reminder.scheduled_at.isoformat()}")
        print(reminder.message)


def print_upcoming(reminders: list[Reminder]) -> None:
    for reminder in reminders:
        print(f"{reminder.scheduled_at:%Y-%m-%d %H:%M}\t{reminder.title}\t{reminder.reminder_id}")


def mac_status_if_needed(now: datetime, config: dict[str, object]) -> str:
    settings = config.get("mac_status", {})
    if not isinstance(settings, dict) or not settings.get("enabled", True):
        return ""
    weekday = WEEKDAYS[str(settings.get("weekday", "sat"))]
    scheduled = datetime.combine(now.date(), parse_time(str(settings.get("notify_time", "10:00"))), tzinfo=now.tzinfo)
    if now.weekday() == weekday and abs(now - scheduled).total_seconds() <= 4 * 60:
        return collect_status()
    return ""


def load_effective_config(settings: Settings) -> dict[str, object]:
    base = load_reminders(settings.reminders_file)
    management = load_management(settings.management_file)
    return merge_config(base, management)


def next_cmd(settings: Settings, days: int, json_output: bool) -> int:
    if days < 0:
        print("[FAIL] days must be >= 0")
        return 1
    config = load_effective_config(settings)
    pattern = load_pattern(settings.pattern_file)
    now = datetime.now(ZoneInfo(settings.timezone)).replace(second=0, microsecond=0)
    reminders = upcoming_reminders(now, config, days, pattern=pattern)
    if json_output:
        rows = [
            {
                "id": reminder.reminder_id,
                "title": reminder.title,
                "scheduled_at": reminder.scheduled_at.isoformat(),
            }
            for reminder in reminders
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not reminders:
        print("No upcoming reminders.")
        return 0
    print_upcoming(reminders)
    return 0


def upcoming_reminders(
    start: datetime,
    config: dict[str, object],
    days: int,
    pattern: MessagePattern | None = None,
) -> list[Reminder]:
    seen: set[str] = set()
    reminders: list[Reminder] = []
    for offset in range(days + 1):
        current_date = (start + timedelta(days=offset)).date()
        probe = datetime.combine(current_date, time(12, 0), tzinfo=start.tzinfo)
        for reminder in scheduled_reminders_near(probe, config, mac_status_text="", pattern=pattern):
            if reminder.scheduled_at.date() != current_date or reminder.scheduled_at < start:
                continue
            if reminder.sent_key in seen:
                continue
            seen.add(reminder.sent_key)
            reminders.append(reminder)
    return sorted(reminders, key=lambda reminder: reminder.scheduled_at)


def list_cmd(settings: Settings, json_output: bool) -> int:
    management = load_management(settings.management_file)
    rows = list_reminders(management, load_effective_config(settings))
    if json_output:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for row in rows:
        status = "disabled" if row.get("enabled") is False else "enabled"
        title = row.get("title") or row["id"]
        schedule = row.get("time") or "-"
        print(f"{row['id']}\t{row['type']}\t{status}\t{schedule}\t{title}")
    return 0


def show_cmd(settings: Settings, reminder_id: str, json_output: bool) -> int:
    row = get_reminder(load_management(settings.management_file), reminder_id, load_effective_config(settings))
    if row is None:
        print(f"[FAIL] unknown reminder: {reminder_id}")
        return 1
    if json_output:
        print(json.dumps(row, ensure_ascii=False, indent=2))
    else:
        for key, value in row.items():
            print(f"{key}: {value}")
    return 0


def enabled_cmd(settings: Settings, reminder_id: str, enabled: bool) -> int:
    try:
        set_enabled(settings.management_file, reminder_id, enabled)
    except ValidationError as exc:
        print(f"[FAIL] {exc}")
        return 1
    print(f"updated {reminder_id}")
    return 0


def remove_cmd(settings: Settings, reminder_id: str) -> int:
    try:
        remove_reminder(settings.management_file, reminder_id)
    except ValidationError as exc:
        print(f"[FAIL] {exc}")
        return 1
    print(f"removed {reminder_id}")
    return 0


def add_cmd(settings: Settings, args: argparse.Namespace) -> int:
    record = {
        "id": args.id,
        "title": args.title,
        "kind": args.kind,
        "time": args.time,
        "action": args.action,
        "note": args.note,
        "enabled": True,
    }
    if args.kind == "one-off":
        record["date"] = args.date
    elif args.kind == "weekly":
        record["weekday"] = args.weekday
    elif args.kind == "interval":
        record["base_date"] = args.base_date
        record["days"] = args.days
    try:
        add_custom(settings.management_file, record)
    except (ValidationError, TypeError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    print(f"added {args.id}")
    return 0


def update_cmd(settings: Settings, args: argparse.Namespace) -> int:
    values = {
        "title": args.title,
        "time": args.time,
        "action": args.action,
        "note": args.note,
        "date": args.date,
        "weekday": args.weekday,
        "base_date": args.base_date,
        "days": args.days,
    }
    try:
        update_reminder(settings.management_file, args.id, values)
    except (ValidationError, TypeError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    print(f"updated {args.id}")
    return 0


def pattern_cmd(settings: Settings, args: argparse.Namespace) -> int:
    if args.pattern_cmd == "show":
        print(json.dumps(load_pattern(settings.pattern_file).__dict__, ensure_ascii=False, indent=2))
        return 0
    pattern = update_pattern(
        settings.pattern_file,
        prefix=args.prefix,
        schedule_label=args.schedule_label,
        action_label=args.action_label,
        note_label=args.note_label,
    )
    print(json.dumps(pattern.__dict__, ensure_ascii=False, indent=2))
    return 0


def validate_cmd(settings: Settings) -> int:
    try:
        validate_management(load_management(settings.management_file))
        load_effective_config(settings)
        load_pattern(settings.pattern_file)
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
