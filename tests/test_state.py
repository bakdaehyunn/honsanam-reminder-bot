from life_reminder.state import SentStore, file_lock


def test_sent_store_prevents_duplicates(tmp_path) -> None:
    store = SentStore(tmp_path / "sent.json")

    assert not store.has("trash:2026-05-12T20:00:00+09:00")
    store.add("trash:2026-05-12T20:00:00+09:00")
    store.add("trash:2026-05-12T20:00:00+09:00")

    assert store.has("trash:2026-05-12T20:00:00+09:00")
    assert store.load() == {"trash:2026-05-12T20:00:00+09:00"}


def test_file_lock_blocks_second_acquire(tmp_path) -> None:
    path = tmp_path / "run.lock"

    with file_lock(path) as first:
        with file_lock(path) as second:
            assert first is True
            assert second is False

    assert not path.exists()
