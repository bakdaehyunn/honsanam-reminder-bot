from life_reminder.cli import diagnose
from life_reminder.config import get_settings, write_default_files


def test_doctor_reports_missing_env(tmp_path) -> None:
    settings = get_settings(tmp_path / ".env")

    lines, ok = diagnose(settings, check_telegram=False)

    assert ok is False
    assert any("env_file missing" in line for line in lines)
    assert any("TELEGRAM_BOT_TOKEN is empty" in line for line in lines)


def test_init_creates_project_env_template(tmp_path) -> None:
    write_default_files(tmp_path)

    env = tmp_path.joinpath(".env").read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN=" in env
    assert "TELEGRAM_REMINDER_CHAT_ID=" in env
    assert "LIFE_REMINDER_TIMEZONE=Asia/Seoul" in env
