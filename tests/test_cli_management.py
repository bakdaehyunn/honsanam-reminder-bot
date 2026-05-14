from pathlib import Path
import tomllib

from life_reminder import cli
from life_reminder.config import Settings, default_reminders_toml
from life_reminder.rules import kst_datetime


def make_settings(tmp_path: Path) -> Settings:
    reminders = tmp_path / "reminders.toml"
    reminders.write_text(default_reminders_toml(), encoding="utf-8")
    return Settings(
        telegram_bot_token="token",
        telegram_reminder_chat_id="-100",
        timezone="Asia/Seoul",
        root=tmp_path,
        env_file=tmp_path / ".env",
        reminders_file=reminders,
        config_dir=tmp_path / ".local/config",
        management_file=tmp_path / ".local/config/reminders.json",
        pattern_file=tmp_path / ".local/config/message_patterns.json",
        state_dir=tmp_path / ".local/state",
        log_dir=tmp_path / ".local/logs",
    )


def test_cli_add_update_disable_list_validate(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    assert cli.main(
        [
            "add",
            "custom",
            "--id",
            "water-plants",
            "--title",
            "화분 물주기",
            "--kind",
            "weekly",
            "--weekday",
            "sat",
            "--time",
            "09:00",
            "--action",
            "화분 물주기",
        ]
    ) == 0
    assert "added water-plants" in capsys.readouterr().out

    assert cli.main(["update", "water-plants", "--time", "09:30"]) == 0
    assert "updated water-plants" in capsys.readouterr().out

    assert cli.main(["disable", "water-plants"]) == 0
    assert "updated water-plants" in capsys.readouterr().out

    assert cli.main(["list", "--json"]) == 0
    output = capsys.readouterr().out
    assert '"id": "water-plants"' in output
    assert '"enabled": false' in output

    assert cli.main(["validate"]) == 0
    assert "valid" in capsys.readouterr().out


def test_cli_pattern_set(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    assert cli.main(["pattern", "set", "--prefix", "알림", "--schedule-label", "시점"]) == 0
    output = capsys.readouterr().out
    assert '"prefix": "알림"' in output
    assert '"schedule_label": "시점"' in output


def test_cli_discover_chat_prints_plain_latest_chat_id(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self) -> dict[str, object]:
            return {
                "ok": True,
                "result": [
                    {"message": {"chat": {"id": 123, "first_name": "Dae"}}},
                    {"message": {"chat": {"id": -100456, "title": "생활알림방", "type": "group"}}},
                ],
            }

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.main(["discover-chat", "--plain"]) == 0
    assert capsys.readouterr().out.strip() == "-100456"


def test_cli_show_uses_effective_fixed_config(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    assert cli.main(["show", "bathroom-cleaning", "--json"]) == 0
    output = capsys.readouterr().out
    assert '"id": "bathroom-cleaning"' in output
    assert '"title": "화장실 청소"' in output
    assert '"time": "10:30"' in output
    assert '"action": "화장실 청소하기"' in output
    assert '"base_date": "2026-05-17"' in output


def test_upcoming_reminders_lists_distributed_defaults() -> None:
    config = tomllib.loads(default_reminders_toml())
    reminders = cli.upcoming_reminders(kst_datetime("2026-05-16", "09:00"), config, 21)

    scheduled = [(reminder.title, reminder.scheduled_at.isoformat()) for reminder in reminders]
    assert ("맥북 상태점검", "2026-05-16T10:00:00+09:00") in scheduled
    assert ("주말 청소", "2026-05-16T14:00:00+09:00") in scheduled
    assert ("손톱 관리", "2026-05-20T21:00:00+09:00") in scheduled
    assert ("화장실 청소", "2026-05-31T10:30:00+09:00") in scheduled
