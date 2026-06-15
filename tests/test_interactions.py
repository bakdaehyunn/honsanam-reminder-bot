from life_reminder.interactions import InteractionStore
from life_reminder.rules import kst_datetime


def test_interaction_store_save_list_and_record_response(tmp_path) -> None:
    store = InteractionStore(tmp_path / "interactions.json")

    store.upsert_sent(
        interaction_id="trash-20260616-2000",
        reminder_id="trash-2026-06-16",
        title="분리수거",
        action="내놨음",
        scheduled_at=kst_datetime("2026-06-16", "20:00"),
    )

    items = store.list_items()
    assert len(items) == 1
    assert items[0]["selected_response"] is None

    store.record_response(
        interaction_id="trash-20260616-2000",
        response="done",
        responded_at=kst_datetime("2026-06-16", "20:05"),
        telegram_update_id=123,
    )

    item = store.list_items()[0]
    assert item["selected_response"] == "done"
    assert item["responded_at"] == "2026-06-16T20:05:00+09:00"
    assert item["telegram_update_id"] == 123
