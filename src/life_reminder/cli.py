from __future__ import annotations

import argparse
import getpass
import json
import subprocess
import sys
import time as time_module
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from life_reminder.confirmations import ConfirmationStore, confirmation_due, parse_datetime
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
    p_poll_replies = sub.add_parser("poll-replies", help="Process Telegram Yes/No confirmation replies")
    p_poll_replies.add_argument("--watch", action="store_true")
    p_poll_replies.add_argument("--watch-iterations", type=int, help=argparse.SUPPRESS)
    p_pending = sub.add_parser("pending", help="List pending confirmations")
    p_pending.add_argument("--json", action="store_true")
    p_answer = sub.add_parser("answer", help="Manually answer a pending confirmation")
    p_answer.add_argument("confirmation_id")
    p_answer.add_argument("answer", choices=["yes", "no"])

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
    if args.cmd == "poll-replies":
        return poll_replies_cmd(settings, watch=args.watch, watch_iterations=args.watch_iterations)
    if args.cmd == "pending":
        return pending_cmd(settings, json_output=args.json)
    if args.cmd == "answer":
        return answer_cmd(settings, args.confirmation_id, args.answer)
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
        doctor_status = 0
    else:
        doctor_status = doctor_cmd(configured)
    if doctor_status != 0:
        print("setup configured but not ready; fix the doctor items above.")
        return doctor_status

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

    print("==> Readiness checklist")
    print(f"[OK] env_file={settings.env_file}")
    print(f"[OK] Telegram reminder chat id configured: {chat_id}")
    print("No test message was sent during setup.")
    print("Next verification command: honsanam-reminder send-test")
    print("setup complete")
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
    latest = candidates[-1]
    print("found Telegram reminder chat candidate")
    print(f"chat_id: {latest.chat_id}")
    print(f"title: {latest.title}")
    print(f"type: {latest.chat_type or '(empty)'}")
    if non_interactive or ask_yes_no("Use this chat as TELEGRAM_REMINDER_CHAT_ID?", default=True):
        return latest.chat_id
    return ""


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
    confirmation_store = ConfirmationStore(settings.state_dir / "confirmations.json")
    regular_pending: list[Reminder] = []
    confirmation_pending: list[Reminder] = []
    for reminder in reminders:
        if is_confirmation_reminder(reminder, config):
            item = confirmation_store.get(reminder.reminder_id)
            if item is None:
                confirmation_pending.append(reminder)
            elif item.get("status") != "completed" and confirmation_due(item, now):
                confirmation_pending.append(reminder_from_confirmation_item(item, now))
            continue
        if not store.has(reminder.sent_key):
            regular_pending.append(reminder)
    followup_pending = [
        reminder_from_confirmation_item(item, now)
        for item in confirmation_store.pending_items()
        if confirmation_due(item, now)
        and not any(reminder.reminder_id == item.get("confirmation_id") for reminder in confirmation_pending)
    ]
    pending = regular_pending + confirmation_pending + followup_pending

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
        for reminder in regular_pending:
            client.send_message(reminder.message)
            store.add(reminder.sent_key)
            print(f"sent {reminder.sent_key}")
        for reminder in confirmation_pending:
            send_confirmation_reminder(client, confirmation_store, reminder, config)
            print(f"sent confirmation {reminder.reminder_id}")
        for reminder in followup_pending:
            send_confirmation_followup(client, confirmation_store, reminder)
            print(f"sent confirmation {reminder.reminder_id}")
    if not pending:
        print("No reminders due.")
    return 0


def is_confirmation_reminder(reminder: Reminder, config: dict[str, object]) -> bool:
    haircut = config.get("haircut", {})
    return (
        reminder.reminder_id.startswith("haircut-booking-")
        and isinstance(haircut, dict)
        and bool(haircut.get("requires_confirmation", False))
    )


def confirmation_prompt(config: dict[str, object]) -> str:
    haircut = config.get("haircut", {})
    if not isinstance(haircut, dict):
        return "완료했나요?"
    return str(haircut.get("confirmation_prompt") or "완료했나요?")


def confirmation_followup_days(config: dict[str, object]) -> int:
    haircut = config.get("haircut", {})
    if not isinstance(haircut, dict):
        return 7
    return int(haircut.get("followup_days", 7))


def confirmation_keyboard(confirmation_id: str) -> dict[str, object]:
    return {
        "inline_keyboard": [
            [
                {"text": "Yes", "callback_data": f"confirm:{confirmation_id}:yes"},
                {"text": "No", "callback_data": f"confirm:{confirmation_id}:no"},
            ]
        ]
    }


def confirmation_message(message: str, prompt: str) -> str:
    return f"{message}\n\n{prompt}"


def send_confirmation_reminder(
    client: TelegramClient,
    store: ConfirmationStore,
    reminder: Reminder,
    config: dict[str, object],
) -> None:
    prompt = confirmation_prompt(config)
    client.send_message(confirmation_message(reminder.message, prompt), reply_markup=confirmation_keyboard(reminder.reminder_id))
    store.upsert_pending(
        confirmation_id=reminder.reminder_id,
        reminder_id=reminder.reminder_id,
        title=reminder.title,
        message=reminder.message,
        prompt=prompt,
        scheduled_at=reminder.scheduled_at,
        prompted_at=reminder.scheduled_at,
        followup_days=confirmation_followup_days(config),
    )


def send_confirmation_followup(client: TelegramClient, store: ConfirmationStore, reminder: Reminder) -> None:
    item = store.get(reminder.reminder_id)
    if item is None:
        return
    client.send_message(reminder.message, reply_markup=confirmation_keyboard(reminder.reminder_id))
    store.upsert_pending(
        confirmation_id=reminder.reminder_id,
        reminder_id=str(item.get("reminder_id") or reminder.reminder_id),
        title=reminder.title,
        message=str(item.get("message") or reminder.message),
        prompt=str(item.get("prompt") or "완료했나요?"),
        scheduled_at=parse_datetime(str(item.get("scheduled_at"))),
        prompted_at=reminder.scheduled_at,
        followup_days=int(item.get("followup_days", 7)),
    )


def reminder_from_confirmation_item(item: dict[str, object], now: datetime) -> Reminder:
    last_prompted_at = parse_datetime(str(item.get("last_prompted_at", "")))
    due_at = last_prompted_at + timedelta(days=int(item.get("followup_days", 7)))
    scheduled_at = due_at.astimezone(now.tzinfo) if due_at.tzinfo is not None and now.tzinfo is not None else due_at
    title = str(item.get("title") or item.get("confirmation_id") or "확인 필요")
    message = confirmation_message(str(item.get("message") or title), str(item.get("prompt") or "완료했나요?"))
    return Reminder(
        reminder_id=str(item.get("confirmation_id") or item.get("reminder_id")),
        scheduled_at=scheduled_at,
        title=title,
        message=message,
    )


def poll_replies_cmd(settings: Settings, watch: bool = False, watch_iterations: int | None = None) -> int:
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    client = TelegramClient(settings.telegram_bot_token, settings.telegram_reminder_chat_id)
    if watch:
        return watch_replies(client, store, settings, max_iterations=watch_iterations)
    return poll_replies_once(client, store, settings, long_poll_timeout=0)


def watch_replies(
    client: TelegramClient,
    store: ConfirmationStore,
    settings: Settings,
    max_iterations: int | None = None,
    long_poll_timeout: int = 50,
    error_backoff_seconds: int = 5,
) -> int:
    print("Watching Telegram confirmation replies.")
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        status = poll_replies_once(
            client,
            store,
            settings,
            long_poll_timeout=long_poll_timeout,
            quiet_no_updates=True,
        )
        if status != 0:
            time_module.sleep(error_backoff_seconds)
    return 0


def poll_replies_once(
    client: TelegramClient,
    store: ConfirmationStore,
    settings: Settings,
    long_poll_timeout: int,
    quiet_no_updates: bool = False,
) -> int:
    try:
        payload = client.get_updates(
            offset=store.offset(),
            timeout=long_poll_timeout,
            allowed_updates=["callback_query"],
        )
    except Exception as exc:
        print(f"[WARN] Telegram getUpdates failed: {exc}")
        return 1
    updates = payload.get("result", []) if isinstance(payload, dict) else []
    if not isinstance(updates, list):
        print("[WARN] Telegram getUpdates returned invalid result")
        return 1
    handled = process_confirmation_updates(client, store, settings, updates)
    if handled == 0 and not quiet_no_updates:
        print("No confirmation replies.")
    return 0


def process_confirmation_updates(
    client: TelegramClient,
    store: ConfirmationStore,
    settings: Settings,
    updates: list[object],
) -> int:
    now = datetime.now(ZoneInfo(settings.timezone)).replace(second=0, microsecond=0)
    handled = 0
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            store.update_offset_if_newer(update_id + 1)
        callback = update.get("callback_query")
        if not isinstance(callback, dict):
            continue
        callback_id = str(callback.get("id") or "")
        data = str(callback.get("data") or "")
        parsed = parse_confirmation_callback(data)
        if parsed is None:
            continue
        confirmation_id, answer = parsed
        try:
            store.mark_answer(confirmation_id, answer, now)
        except KeyError:
            if callback_id:
                answer_callback_query_safely(client, callback_id, "알림을 찾을 수 없습니다.")
            print(f"unknown confirmation: {confirmation_id}")
            continue
        if callback_id:
            answer_callback_query_safely(client, callback_id, "완료 처리했습니다." if answer == "yes" else "다음에 다시 물어볼게요.")
        print(f"answered {confirmation_id}: {answer}")
        handled += 1
    return handled


def answer_callback_query_safely(client: TelegramClient, callback_query_id: str, text: str) -> None:
    try:
        client.answer_callback_query(callback_query_id, text)
    except Exception as exc:
        print(f"[WARN] Telegram answerCallbackQuery failed: {exc}")


def parse_confirmation_callback(data: str) -> tuple[str, str] | None:
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "confirm" or parts[2] not in {"yes", "no"}:
        return None
    return parts[1], parts[2]


def pending_cmd(settings: Settings, json_output: bool) -> int:
    items = ConfirmationStore(settings.state_dir / "confirmations.json").pending_items()
    if json_output:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    if not items:
        print("No pending confirmations.")
        return 0
    for item in items:
        print(
            f"{item.get('confirmation_id')}\t{item.get('status')}\t"
            f"last_prompted={item.get('last_prompted_at')}\t{item.get('title')}"
        )
    return 0


def answer_cmd(settings: Settings, confirmation_id: str, answer: str) -> int:
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    now = datetime.now(ZoneInfo(settings.timezone)).replace(second=0, microsecond=0)
    try:
        store.mark_answer(confirmation_id, answer, now)
    except KeyError:
        print(f"[FAIL] unknown confirmation: {confirmation_id}")
        return 1
    print(f"answered {confirmation_id}: {answer}")
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
