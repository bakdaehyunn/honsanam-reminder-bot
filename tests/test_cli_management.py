from pathlib import Path

from life_reminder import cli
from life_reminder.config import Settings


def make_settings(tmp_path: Path) -> Settings:
    reminders = tmp_path / "reminders.toml"
    reminders.write_text("[haircut]\nenabled = true\n", encoding="utf-8")
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
