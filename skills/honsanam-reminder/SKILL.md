---
name: honsanam-reminder
description: Use when managing the 혼사남 알림봇 project through its honsanam-reminder CLI, including setup, Telegram chat discovery, health checks, previews, scheduled sends, fixed reminder management, custom reminder CRUD, message pattern changes, validation, and launchd-oriented verification.
---

# Honsanam Reminder

Use this skill to operate the `honsanam-reminder` CLI for 혼사남 알림봇. The CLI is the supported interface for routine changes; avoid editing `.local/config/*.json` directly unless the CLI cannot express the requested change.

Fixed reminder IDs: `haircut`, `fingernails`, `toenails`, `nose-hair`, `earwax`, `trash`, `mac-status`, `weekend-cleaning`, `bedding-wash`, `bathroom-cleaning`.

Default schedule philosophy: avoid piling reminders into one day or time block. Prefer small, separated routines that are easy to act on one at a time.

## Operating Rules

- Work from the project root: `/Users/hennei/workspace/honsanam-reminder-bot`.
- Prefer dry-run and read-only commands before sends or config changes.
- Do not run `send-test` or non-dry-run `run-once` without explicit user approval because they can send Telegram messages.
- After any add, update, enable, disable, remove, or pattern change, run `honsanam-reminder validate`.
- Use Korean titles, actions, and notes for user-facing reminder text unless the user asks otherwise.
- Reminder IDs must be lowercase kebab-case and match `^[a-z][a-z0-9-]{1,63}$`.
- Times use 24-hour `HH:MM`; dates use `YYYY-MM-DD`; weekdays are `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`.

## Command Map

### `init`

Create default local files and directories:

```bash
honsanam-reminder init
```

Use for first setup or to restore missing default files. It creates `.env.example`, `.env`, `reminders.toml`, and `.local/` subdirectories when missing.

### `setup`

Configure local env values, Telegram chat discovery, checks, upcoming reminders, and optional launchd install:

```bash
honsanam-reminder setup
honsanam-reminder setup --dry-run
honsanam-reminder setup --non-interactive --telegram-bot-token "$TOKEN" --telegram-chat-id "$CHAT_ID" --timezone Asia/Seoul
```

Use this as the standard first setup or reconfiguration command after the CLI is installed. It does not send a Telegram test message; ask for approval before running `send-test`.

### `doctor`

Check runtime configuration and Telegram connectivity:

```bash
honsanam-reminder doctor
```

Use when setup, Telegram delivery, file permissions, or config health is uncertain. It may call Telegram `getMe` when a bot token is configured.

### `discover-chat`

Find the Telegram chat id from recent bot updates:

```bash
honsanam-reminder discover-chat
honsanam-reminder discover-chat --plain
honsanam-reminder discover-chat --json
```

Use as a helper when only the Telegram chat id is needed. `setup` uses the same discovery behavior. `--plain` prints only the latest chat id and is useful for scripts. This calls Telegram `getUpdates`, but does not send a message.

### `preview`

Preview reminders due at a specific KST date and time without sending:

```bash
honsanam-reminder preview --date 2026-06-01 --time 08:45
```

Use before changing schedules or explaining what will fire at a given time.

### `next`

Show upcoming reminders without sending:

```bash
honsanam-reminder next --days 14
honsanam-reminder next --days 14 --json
```

Use when checking whether the default routines are distributed well or when explaining the upcoming schedule.

### `run-once`

Evaluate reminders due now:

```bash
honsanam-reminder run-once --dry-run
honsanam-reminder run-once
```

Use `--dry-run` for verification. Use non-dry-run only after explicit user approval; it can send Telegram messages and update `.local/state/sent.json`, `.local/state/confirmations.json`, and `.local/state/interactions.json`.

### `poll-replies`

Process Telegram confirmation and lightweight interaction button replies:

```bash
honsanam-reminder poll-replies
honsanam-reminder poll-replies --watch
```

Use one-shot mode when checking whether Telegram button answers have been applied. Use `--watch` for the launchd reply watcher; it uses Telegram long polling and keeps running so inline button loading clears quickly. This reads Telegram `getUpdates`, updates confirmation or interaction state, and answers callback queries.

### `pending`

List pending Yes/No confirmations:

```bash
honsanam-reminder pending
honsanam-reminder pending --json
```

Use when the user asks what still needs confirmation.

### `interactions`

List stored lightweight interaction responses:

```bash
honsanam-reminder interactions
honsanam-reminder interactions --json
```

Use when the user asks what routine buttons have been clicked. These records are for future stats and do not create follow-up reminders.

### `answer`

Manually answer a confirmation:

```bash
honsanam-reminder answer haircut-booking-2026-06-07 yes
honsanam-reminder answer haircut-booking-2026-06-07 no
```

Use as a fallback if Telegram buttons were missed. `yes` completes that confirmation cycle; `no` keeps it pending for the next follow-up.

### `send-test`

Send a Telegram test message:

```bash
honsanam-reminder send-test
```

Use only after explicit user approval. This verifies that the configured chat receives messages.

### `list`

List configured reminder IDs:

```bash
honsanam-reminder list
honsanam-reminder list --json
```

Use `--json` when another tool or agent needs structured output.

### `show`

Inspect one reminder:

```bash
honsanam-reminder show trash
honsanam-reminder show trash --json
```

Use before updating or disabling a reminder so the current state is visible.

### `enable` / `disable`

Toggle a fixed or custom reminder:

```bash
honsanam-reminder enable trash
honsanam-reminder disable trash
```

Run `honsanam-reminder validate` afterward.

### `add custom`

Add a custom reminder. Required common fields: `--id`, `--title`, `--kind`, `--time`, `--action`.

One-off:

```bash
honsanam-reminder add custom --id passport-check --title "여권 확인" --kind one-off --date 2026-06-01 --time 09:00 --action "여권 만료일 확인"
```

Weekly:

```bash
honsanam-reminder add custom --id water-plants --title "화분 물주기" --kind weekly --weekday sat --time 09:00 --action "화분 물주기"
```

Interval:

```bash
honsanam-reminder add custom --id towel-wash --title "수건 세탁" --kind interval --base-date 2026-05-10 --days 7 --time 10:00 --action "수건 세탁하기"
```

Optional: add `--note "..."` for extra message detail. Run `validate` after adding.

### `update`

Update a fixed or custom reminder:

```bash
honsanam-reminder update water-plants --time 09:30 --note "거실 먼저 확인"
```

For fixed reminders, supported fields are constrained by the underlying fixed type. For custom reminders, update only the fields that need changing. Run `show <id> --json` before and `validate` after.

### `remove`

Remove a custom reminder:

```bash
honsanam-reminder remove water-plants
```

Fixed reminders cannot be removed; disable them instead. Confirm with the user before removing.

### `pattern show` / `pattern set`

Inspect or update message labels:

```bash
honsanam-reminder pattern show
honsanam-reminder pattern set --prefix "생활알림" --schedule-label "언제" --action-label "해야 할 일" --note-label "관리 포인트"
```

Use when the user wants message wording or labels changed globally. Run `preview` afterward to inspect a rendered message.

### `validate`

Validate management config, merged reminder config, and message pattern:

```bash
honsanam-reminder validate
```

Run after every config-changing command and before touching launchd.

## Common Workflows

Add a new routine:

1. Convert the user request into `one-off`, `weekly`, or `interval`.
2. Choose a stable kebab-case ID.
3. Run `add custom`.
4. Run `validate`.
5. Run `preview` for the next expected schedule if the user wants confirmation.

Change an existing routine:

1. Run `list --json` or `show <id> --json`.
2. Run `update`, `enable`, or `disable`.
3. Run `validate`.
4. Use `preview` when schedule behavior matters.
5. Use `next --days 14` when checking whether changes make reminders pile up.

Verify delivery:

1. Run `setup` for first setup or reconfiguration.
2. Run `doctor`.
3. Run `poll-replies`.
4. Run `run-once --dry-run`.
5. Ask for approval before `send-test` or `run-once`.

Verify launchd:

1. Run `scripts/install_launch_agent.sh`.
2. Confirm `com.hennei.honsanam-reminder-bot.replies` runs `poll-replies --watch` with `KeepAlive`.
3. Confirm `com.hennei.honsanam-reminder-bot.sender` runs `run-once` with `StartCalendarInterval` at 08:45, 10:00, 14:00, 20:00, 20:30, and 21:00.
