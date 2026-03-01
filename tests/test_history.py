import pytest
from phantom.history import History


@pytest.fixture
def history(tmp_path):
    return History(tmp_path)


def test_add_and_get_entries(history):
    history.add("Hello world", "paste")
    history.add("Buy groceries", "notes")
    entries = history.get_all()
    assert len(entries) == 2
    assert entries[0]["text"] == "Buy groceries"  # Most recent first
    assert entries[0]["mode"] == "notes"
    assert entries[1]["text"] == "Hello world"
    assert entries[1]["mode"] == "paste"


def test_entries_have_timestamps(history):
    history.add("Test entry", "paste")
    entries = history.get_all()
    assert "timestamp" in entries[0]
    assert len(entries[0]["timestamp"]) > 0


def test_max_50_entries(history):
    for i in range(55):
        history.add(f"Entry {i}", "paste")
    entries = history.get_all()
    assert len(entries) == 50
    # Oldest 5 should be pruned
    assert entries[-1]["text"] == "Entry 5"


def test_get_entry_by_id(history):
    history.add("Find me", "paste")
    entries = history.get_all()
    entry = history.get_by_id(entries[0]["id"])
    assert entry["text"] == "Find me"


def test_empty_history(history):
    entries = history.get_all()
    assert entries == []
