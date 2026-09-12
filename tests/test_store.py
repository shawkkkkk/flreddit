from flreddit import Forum, SQLiteStore


def test_sqlite_store_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "flreddit.sqlite3")
    forum = Forum(seed=77)
    for _ in range(12):
        forum.step()
    saved_at = store.save(forum)

    restored = store.load()
    assert restored is not None
    assert restored.snapshot() == forum.snapshot()
    assert store.status()["has_snapshot"] is True
    assert store.status()["saved_at"] == saved_at
    assert store.status()["compressed_bytes"] > 0


def test_empty_store_has_no_forum(tmp_path):
    store = SQLiteStore(tmp_path / "empty.sqlite3")
    assert store.load() is None
    assert store.status()["has_snapshot"] is False
