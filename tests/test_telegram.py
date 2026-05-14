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
