from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = ROOT / ".env"
DEFAULT_REMINDERS_FILE = ROOT / "reminders.toml"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_reminder_chat_id: str
    timezone: str
    root: Path
    env_file: Path
    reminders_file: Path
    config_dir: Path
    management_file: Path
    pattern_file: Path
    state_dir: Path
    log_dir: Path


def load_env(path: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def get_settings(env_file: Path = DEFAULT_ENV_FILE) -> Settings:
    env = load_env(env_file)
    root = env_file.resolve().parent
    return Settings(
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_reminder_chat_id=env.get("TELEGRAM_REMINDER_CHAT_ID", "").strip(),
        timezone=env.get("LIFE_REMINDER_TIMEZONE", "Asia/Seoul").strip() or "Asia/Seoul",
        root=root,
        env_file=env_file,
        reminders_file=root / "reminders.toml",
        config_dir=root / ".local/config",
        management_file=root / ".local/config/reminders.json",
        pattern_file=root / ".local/config/message_patterns.json",
        state_dir=root / ".local/state",
        log_dir=root / ".local/logs",
    )


def load_reminders(path: Path = DEFAULT_REMINDERS_FILE) -> dict[str, Any]:
    with path.open("rb") as f:
        payload = tomllib.load(f)
    return payload


def write_default_files(root: Path = ROOT) -> list[str]:
    created: list[str] = []
    env_example = root / ".env.example"
    env_file = root / ".env"
    reminders = root / "reminders.toml"
    state_dir = root / ".local/state"
    log_dir = root / ".local/logs"
    config_dir = root / ".local/config"

    state_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    if not env_example.exists():
        env_example.write_text(
            "TELEGRAM_BOT_TOKEN=\n"
            "TELEGRAM_REMINDER_CHAT_ID=\n"
            "LIFE_REMINDER_TIMEZONE=Asia/Seoul\n",
            encoding="utf-8",
        )
        created.append(str(env_example))

    if not reminders.exists():
        reminders.write_text(default_reminders_toml(), encoding="utf-8")
        created.append(str(reminders))

    if not env_file.exists():
        env_file.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(str(env_file))

    return created


def default_reminders_toml() -> str:
    return """[haircut]
enabled = true
base_date = "2026-05-10"
interval_months = 1
notify_time = "08:45"
weekend_policy = "previous_sunday"

[nails]
enabled = true
base_date = "2026-05-10"
fingernails_days = 7
toenails_days = 21
notify_time = "20:00"

[trash]
enabled = true
weekdays = ["tue", "thu", "sun"]
notify_time = "20:00"

[mac_status]
enabled = true
weekday = "sat"
notify_time = "10:00"

[cleaning]
enabled = true
weekday = "sat"
notify_time = "10:30"
"""


def set_env_for_process(env_file: Path = DEFAULT_ENV_FILE) -> None:
    for key, value in load_env(env_file).items():
        os.environ.setdefault(key, value)
