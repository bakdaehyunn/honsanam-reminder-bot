from datetime import timedelta

from life_reminder.confirmations import ConfirmationStore, confirmation_due
from life_reminder.rules import kst_datetime


def test_confirmation_store_create_list_yes_no_and_offset(tmp_path) -> None:
    store = ConfirmationStore(tmp_path / "confirmations.json")
    prompted_at = kst_datetime("2026-06-01", "08:45")

    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=prompted_at,
        prompted_at=prompted_at,
        followup_days=7,
    )
    assert [item["confirmation_id"] for item in store.pending_items()] == ["haircut-booking-2026-06-07"]

    store.mark_answer("haircut-booking-2026-06-07", "no", prompted_at + timedelta(hours=1))
    assert store.get("haircut-booking-2026-06-07")["status"] == "pending"
    assert store.get("haircut-booking-2026-06-07")["last_answer"] == "no"

    store.mark_answer("haircut-booking-2026-06-07", "yes", prompted_at + timedelta(hours=2))
    assert store.get("haircut-booking-2026-06-07")["status"] == "completed"
    assert store.pending_items() == []
    store.mark_answer("haircut-booking-2026-06-07", "no", prompted_at + timedelta(hours=3))
    assert store.get("haircut-booking-2026-06-07")["status"] == "pending"
    assert store.get("haircut-booking-2026-06-07")["completed_at"] is None

    store.update_offset_if_newer(10)
    store.update_offset_if_newer(5)
    assert store.offset() == 10


def test_confirmation_followup_due_after_configured_days(tmp_path) -> None:
    store = ConfirmationStore(tmp_path / "confirmations.json")
    prompted_at = kst_datetime("2026-06-01", "08:45")
    store.upsert_pending(
        confirmation_id="haircut-booking-2026-06-07",
        reminder_id="haircut-booking-2026-06-07",
        title="미용실 예약",
        message="message",
        prompt="미용실 예약했나요?",
        scheduled_at=prompted_at,
        prompted_at=prompted_at,
        followup_days=7,
    )
    item = store.get("haircut-booking-2026-06-07")

    assert not confirmation_due(item, kst_datetime("2026-06-08", "08:40"))
    assert confirmation_due(item, kst_datetime("2026-06-08", "08:45"))

    store.mark_answer("haircut-booking-2026-06-07", "yes", kst_datetime("2026-06-01", "09:00"))
    assert not confirmation_due(store.get("haircut-booking-2026-06-07"), kst_datetime("2026-06-08", "08:45"))
