import pytest
from phantom.notes import append_note


@pytest.fixture
def notes_file(tmp_path):
    return tmp_path / "notes.md"


def test_append_creates_file_if_missing(notes_file):
    append_note("First note", notes_file)
    assert notes_file.exists()
    content = notes_file.read_text(encoding="utf-8")
    assert "First note" in content


def test_append_adds_timestamp_header(notes_file):
    append_note("Test note", notes_file)
    content = notes_file.read_text(encoding="utf-8")
    # Should have a ## YYYY-MM-DD HH:MM header
    assert content.startswith("## ")


def test_multiple_appends(notes_file):
    append_note("Note one", notes_file)
    append_note("Note two", notes_file)
    content = notes_file.read_text(encoding="utf-8")
    assert "Note one" in content
    assert "Note two" in content
    # Should have two headers
    assert content.count("## ") == 2


def test_notes_separated_by_blank_lines(notes_file):
    append_note("First", notes_file)
    append_note("Second", notes_file)
    content = notes_file.read_text(encoding="utf-8")
    # Each entry should be separated
    assert "\n\n" in content
