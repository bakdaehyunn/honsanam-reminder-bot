import json

from life_reminder.telegram import TelegramClient
from life_reminder.telegram import discover_chat_candidates


def test_discover_chat_candidates_reads_recent_message_chats() -> None:
    payload = {
        "ok": True,
        "result": [
            {"message": {"chat": {"id": 123, "first_name": "Dae"}}},
            {"message": {"chat": {"id": -100456, "title": "생활알림방", "type": "group"}}},
        ],
    }

    candidates = discover_chat_candidates(payload)

    assert [candidate.chat_id for candidate in candidates] == ["123", "-100456"]
    assert candidates[-1].title == "생활알림방"
    assert candidates[-1].chat_type == "group"


def test_discover_chat_candidates_ignores_duplicate_chats() -> None:
    payload = {
        "ok": True,
        "result": [
            {"message": {"chat": {"id": -100456, "title": "생활알림방"}}},
            {"edited_message": {"chat": {"id": -100456, "title": "생활알림방"}}},
        ],
    }

    candidates = discover_chat_candidates(payload)

    assert len(candidates) == 1
    assert candidates[0].chat_id == "-100456"


def test_send_message_passes_inline_keyboard_reply_markup(monkeypatch) -> None:
    calls = []
    client = TelegramClient("token", "-100")

    def fake_api(method_name, params, method="GET"):
        calls.append((method_name, params, method))
        return {"ok": True, "result": {}}

    monkeypatch.setattr(client, "_api", fake_api)
    client.send_message(
        "미용실 예약했나요?",
        reply_markup={
            "inline_keyboard": [
                [
                    {"text": "Yes", "callback_data": "confirm:haircut-booking-2026-06-07:yes"},
                    {"text": "No", "callback_data": "confirm:haircut-booking-2026-06-07:no"},
                ]
            ]
        },
    )

    assert calls[0][0] == "sendMessage"
    assert calls[0][2] == "POST"
    assert json.loads(calls[0][1]["reply_markup"])["inline_keyboard"][0][0]["text"] == "Yes"


def test_answer_callback_query_posts_callback_response(monkeypatch) -> None:
    calls = []
    client = TelegramClient("token", "-100")

    def fake_api(method_name, params, method="GET"):
        calls.append((method_name, params, method))
        return {"ok": True, "result": {}}

    monkeypatch.setattr(client, "_api", fake_api)
    client.answer_callback_query("callback-id", "완료 처리했습니다.")

    assert calls == [
        (
            "answerCallbackQuery",
            {"callback_query_id": "callback-id", "text": "완료 처리했습니다."},
            "POST",
        )
    ]
