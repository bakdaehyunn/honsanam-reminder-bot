from pathlib import Path
import tomllib

import pytest

from life_reminder import cli
from life_reminder.confirmations import ConfirmationStore
from life_reminder.config import Settings, default_reminders_toml, load_env
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


def test_cli_setup_help_is_available(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["setup", "--help"])

    assert exc.value.code == 0
    assert "usage: honsanam-reminder setup" in capsys.readouterr().out


def test_setup_non_interactive_writes_env_without_printing_secret(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_me(self) -> dict[str, object]:
            return {"ok": True, "result": {"username": "honsanam_bot"}}

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert (
        cli.setup_cmd(
            settings,
            dry_run=False,
            non_interactive=True,
            telegram_bot_token="secret-token",
            telegram_chat_id="-100123",
            timezone="Asia/Seoul",
            install_launchd=False,
        )
        == 0
    )

    env = load_env(settings.env_file)
    assert env["TELEGRAM_BOT_TOKEN"] == "secret-token"
    assert env["TELEGRAM_REMINDER_CHAT_ID"] == "-100123"
    assert env["LIFE_REMINDER_TIMEZONE"] == "Asia/Seoul"
    assert "secret-token" not in capsys.readouterr().out


def test_setup_non_interactive_discovers_chat_id(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self) -> dict[str, object]:
            return {"ok": True, "result": [{"message": {"chat": {"id": -100456, "title": "생활알림방"}}}]}

        def get_me(self) -> dict[str, object]:
            return {"ok": True, "result": {"username": "honsanam_bot"}}

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert (
        cli.setup_cmd(
            settings,
            dry_run=False,
            non_interactive=True,
            telegram_bot_token="secret-token",
            telegram_chat_id=None,
            timezone="Asia/Seoul",
            install_launchd=False,
        )
        == 0
    )

    assert load_env(settings.env_file)["TELEGRAM_REMINDER_CHAT_ID"] == "-100456"


def test_setup_stops_when_doctor_fails(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)
    monkeypatch.setattr(cli, "doctor_cmd", lambda configured: 1)

    assert (
        cli.setup_cmd(
            settings,
            dry_run=False,
            non_interactive=True,
            telegram_bot_token="secret-token",
            telegram_chat_id="-100123",
            timezone="Asia/Seoul",
            install_launchd=False,
        )
        == 1
    )

    out = capsys.readouterr().out
    assert "setup configured but not ready" in out
    assert "setup complete" not in out


def test_discover_chat_for_setup_requires_interactive_confirmation(monkeypatch, capsys) -> None:
    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self) -> dict[str, object]:
            return {"ok": True, "result": [{"message": {"chat": {"id": -100456, "title": "생활알림방"}}}]}

    answers = iter(["y", "", "n"])
    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert cli.discover_chat_for_setup("token", dry_run=False, non_interactive=False) == ""
    out = capsys.readouterr().out
    assert "chat_id: -100456" in out
    assert "title: 생활알림방" in out


def test_setup_non_interactive_can_install_launchd_when_requested(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    calls: list[tuple[Path, bool]] = []

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_me(self) -> dict[str, object]:
            return {"ok": True, "result": {"username": "honsanam_bot"}}

    def fake_install_launch_agent(root: Path, dry_run: bool) -> int:
        calls.append((root, dry_run))
        return 0

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)
    monkeypatch.setattr(cli, "install_launch_agent", fake_install_launch_agent)
    monkeypatch.setattr(cli.sys, "platform", "darwin")

    assert (
        cli.setup_cmd(
            settings,
            dry_run=False,
            non_interactive=True,
            telegram_bot_token="secret-token",
            telegram_chat_id="-100123",
            timezone="Asia/Seoul",
            install_launchd=True,
        )
        == 0
    )
    assert calls == [(tmp_path, False)]


def test_setup_non_interactive_fails_when_chat_id_is_missing(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self) -> dict[str, object]:
            return {"ok": True, "result": []}

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert (
        cli.setup_cmd(
            settings,
            dry_run=False,
            non_interactive=True,
            telegram_bot_token="secret-token",
            telegram_chat_id=None,
            timezone="Asia/Seoul",
            install_launchd=False,
        )
        == 1
    )
    assert "Telegram reminder chat id is required" in capsys.readouterr().out


def test_prompt_setup_value_keeps_existing_value_on_empty_input(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    assert cli.prompt_setup_value("Timezone", "Asia/Seoul", secret=False) == "Asia/Seoul"


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


def test_poll_replies_processes_yes_callback_and_stores_offset(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )
    answered_callbacks = []

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self, offset=None, timeout=None, allowed_updates=None) -> dict[str, object]:
            assert offset is None
            assert timeout == 0
            assert allowed_updates == ["callback_query"]
            return {
                "ok": True,
                "result": [
                    {
                        "update_id": 100,
                        "callback_query": {
                            "id": "cb-1",
                            "data": "confirm:haircut-booking-2026-06-07:yes",
                        },
                    }
                ],
            }

        def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
            answered_callbacks.append((callback_query_id, text))

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.poll_replies_cmd(settings) == 0
    assert store.get("haircut-booking-2026-06-07")["status"] == "completed"
    assert store.offset() == 101
    assert answered_callbacks == [("cb-1", "완료 처리했습니다.")]
    assert "answered haircut-booking-2026-06-07: yes" in capsys.readouterr().out


def test_poll_replies_processes_no_callback_without_completion(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )
    store.update_offset(101)

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self, offset=None, timeout=None, allowed_updates=None) -> dict[str, object]:
            assert offset == 101
            assert timeout == 0
            assert allowed_updates == ["callback_query"]
            return {
                "ok": True,
                "result": [
                    {
                        "update_id": 101,
                        "callback_query": {
                            "id": "cb-2",
                            "data": "confirm:haircut-booking-2026-06-07:no",
                        },
                    }
                ],
            }

        def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
            pass

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.poll_replies_cmd(settings) == 0
    item = store.get("haircut-booking-2026-06-07")
    assert item["status"] == "pending"
    assert item["last_answer"] == "no"
    assert store.offset() == 102


def test_poll_replies_keeps_answer_when_callback_ack_fails(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self, offset=None, timeout=None, allowed_updates=None) -> dict[str, object]:
            assert timeout == 0
            assert allowed_updates == ["callback_query"]
            return {
                "ok": True,
                "result": [
                    {
                        "update_id": 200,
                        "callback_query": {
                            "id": "expired-callback",
                            "data": "confirm:haircut-booking-2026-06-07:no",
                        },
                    }
                ],
            }

        def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
            raise RuntimeError("callback query is too old")

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.poll_replies_cmd(settings) == 0
    item = store.get("haircut-booking-2026-06-07")
    assert item["status"] == "pending"
    assert item["last_answer"] == "no"
    out = capsys.readouterr().out
    assert "[WARN] Telegram answerCallbackQuery failed" in out
    assert "answered haircut-booking-2026-06-07: no" in out


def test_poll_replies_watch_uses_long_polling_and_can_stop_in_tests(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    calls = []

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self, offset=None, timeout=None, allowed_updates=None) -> dict[str, object]:
            calls.append((offset, timeout, allowed_updates))
            return {"ok": True, "result": []}

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.main(["poll-replies", "--watch", "--watch-iterations", "2"]) == 0
    assert calls == [
        (None, 50, ["callback_query"]),
        (None, 50, ["callback_query"]),
    ]
    assert "Watching Telegram confirmation replies." in capsys.readouterr().out


def test_poll_replies_watch_handles_api_errors_and_continues(tmp_path, monkeypatch, capsys) -> None:
    settings = make_settings(tmp_path)
    calls = 0

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def get_updates(self, offset=None, timeout=None, allowed_updates=None) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("network down")
            return {"ok": True, "result": []}

    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)
    monkeypatch.setattr(cli.time_module, "sleep", lambda seconds: None)

    assert cli.poll_replies_cmd(settings, watch=True, watch_iterations=2) == 0
    assert calls == 2
    assert "[WARN] Telegram getUpdates failed: network down" in capsys.readouterr().out


def test_pending_and_answer_commands(tmp_path, capsys) -> None:
    settings = make_settings(tmp_path)
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )

    assert cli.pending_cmd(settings, json_output=False) == 0
    assert "haircut-booking-2026-06-07" in capsys.readouterr().out

    assert cli.answer_cmd(settings, "haircut-booking-2026-06-07", "yes") == 0
    assert store.get("haircut-booking-2026-06-07")["status"] == "completed"


def test_run_once_sends_haircut_confirmation_with_buttons(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    sent = []

    class FixedDatetime(cli.datetime):
        @classmethod
        def now(cls, tz=None):
            return kst_datetime("2026-06-01", "08:45")

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def send_message(self, text: str, reply_markup=None) -> None:
            sent.append((text, reply_markup))

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.run_once_cmd(settings, dry_run=False) == 0
    assert len(sent) == 1
    assert "미용실 예약했나요?" in sent[0][0]
    assert sent[0][1]["inline_keyboard"][0][0]["callback_data"] == "confirm:haircut-booking-2026-06-07:yes"
    assert ConfirmationStore(settings.state_dir / "confirmations.json").get("haircut-booking-2026-06-07")["status"] == "pending"


def test_run_once_does_not_resend_pending_confirmation_before_followup(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    sent = []
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )

    class FixedDatetime(cli.datetime):
        @classmethod
        def now(cls, tz=None):
            return kst_datetime("2026-06-08", "08:40")

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def send_message(self, text: str, reply_markup=None) -> None:
            sent.append((text, reply_markup))

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.run_once_cmd(settings, dry_run=False) == 0
    assert sent == []


def test_run_once_resends_pending_confirmation_after_followup_days(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    sent = []
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )

    class FixedDatetime(cli.datetime):
        @classmethod
        def now(cls, tz=None):
            return kst_datetime("2026-06-08", "08:45")

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def send_message(self, text: str, reply_markup=None) -> None:
            sent.append((text, reply_markup))

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.run_once_cmd(settings, dry_run=False) == 0
    assert len(sent) == 1
    assert "미용실 예약했나요?" in sent[0][0]
    assert store.get("haircut-booking-2026-06-07")["last_prompted_at"] == "2026-06-08T08:45:00+09:00"


def test_run_once_suppresses_completed_confirmation_followup(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    sent = []
    store = ConfirmationStore(settings.state_dir / "confirmations.json")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=kst_datetime("2026-06-01", "08:45"),
        prompted_at=kst_datetime("2026-06-01", "08:45"),
        followup_days=7,
    )
    store.mark_answer("haircut-booking-2026-06-07", "yes", kst_datetime("2026-06-01", "09:00"))

    class FixedDatetime(cli.datetime):
        @classmethod
        def now(cls, tz=None):
            return kst_datetime("2026-06-08", "08:45")

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def send_message(self, text: str, reply_markup=None) -> None:
            sent.append((text, reply_markup))

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.run_once_cmd(settings, dry_run=False) == 0
    assert sent == []


def test_run_once_keeps_non_confirmation_reminders_unchanged(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    sent = []

    class FixedDatetime(cli.datetime):
        @classmethod
        def now(cls, tz=None):
            return kst_datetime("2026-05-19", "20:00")

    class FakeTelegramClient:
        def __init__(self, token: str, chat_id: str) -> None:
            self.token = token
            self.chat_id = chat_id

        def send_message(self, text: str, reply_markup=None) -> None:
            sent.append((text, reply_markup))

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "TelegramClient", FakeTelegramClient)

    assert cli.run_once_cmd(settings, dry_run=False) == 0
    assert len(sent) == 1
    assert "분리수거" in sent[0][0]
    assert sent[0][1] is None


def test_upcoming_reminders_lists_distributed_defaults() -> None:
    config = tomllib.loads(default_reminders_toml())
    reminders = cli.upcoming_reminders(kst_datetime("2026-05-16", "09:00"), config, 21)

    scheduled = [(reminder.title, reminder.scheduled_at.isoformat()) for reminder in reminders]
    assert ("맥북 상태점검", "2026-05-16T10:00:00+09:00") in scheduled
    assert ("주말 청소", "2026-05-16T14:00:00+09:00") in scheduled
    assert ("손톱 관리", "2026-05-20T21:00:00+09:00") in scheduled
    assert ("코털 정리", "2026-05-22T20:30:00+09:00") in scheduled
    assert ("귀지 정리", "2026-05-25T21:00:00+09:00") in scheduled
    assert ("화장실 청소", "2026-05-31T10:30:00+09:00") in scheduled
